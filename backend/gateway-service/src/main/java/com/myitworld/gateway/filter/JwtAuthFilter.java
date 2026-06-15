package com.myitworld.gateway.filter;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.myitworld.common.constant.AuthConstants;
import com.myitworld.common.result.Result;
import com.myitworld.common.result.ResultCode;
import com.myitworld.common.util.JwtUtil;
import com.myitworld.gateway.config.GatewayWhitelistProperties;
import com.myitworld.gateway.config.JwtProperties;
import io.jsonwebtoken.Claims;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.stream.Collectors;

/**
 * JWT 鉴权全局过滤器
 * <p>
 * 在 Gateway 层统一校验 JWT，避免每个微服务重复实现鉴权逻辑。
 * 处理流程：
 * 1. 检查请求路径是否在白名单 → 是则直接放行
 * 2. 从 Authorization 头提取 Token → 缺失则返回 401
 * 3. 解析并校验 Token 签名与过期时间
 * 4. 检查 Token 是否在 Redis 黑名单（已登出）
 * 5. 校验通过 → 将 userId、username、roles 写入请求头传递给下游服务
 * </p>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthFilter implements GlobalFilter, Ordered {

    private final JwtProperties jwtProperties;
    private final GatewayWhitelistProperties whitelistProperties;
    private final ReactiveStringRedisTemplate reactiveRedisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();

        // 1. 白名单路径：无 Token 也可访问；若带了有效 Token 则注入用户信息（供 ai-service 绑定会话）
        if (isWhitelisted(path) || isPublicBlogRead(path, request.getMethod())
                || isPublicContentRead(path, request.getMethod())
                || isPublicFileRead(path, request.getMethod())) {
            return filterWithOptionalAuth(exchange, chain, request);
        }

        // 2. 提取 Token
        String authHeader = request.getHeaders().getFirst(AuthConstants.TOKEN_HEADER);
        String token = JwtUtil.extractToken(authHeader);

        if (!StringUtils.hasText(token)) {
            return unauthorizedResponse(exchange, ResultCode.UNAUTHORIZED);
        }

        // 3. 解析 Token
        Claims claims;
        try {
            claims = JwtUtil.parseToken(token, jwtProperties.getSecret());
        } catch (Exception e) {
            log.warn("Token 解析失败: path={}, error={}", path, e.getMessage());
            return unauthorizedResponse(exchange, ResultCode.TOKEN_INVALID);
        }

        // 4. 必须是 Access Token（Refresh Token 不能用于 API 访问）
        if (!JwtUtil.isAccessToken(claims)) {
            return unauthorizedResponse(exchange, ResultCode.TOKEN_INVALID);
        }

        // 5. 检查黑名单（异步 Reactive Redis）
        String jti = JwtUtil.getJti(claims);
        String blacklistKey = AuthConstants.REDIS_BLACKLIST_PREFIX + jti;

        return reactiveRedisTemplate.hasKey(blacklistKey)
                .flatMap(inBlacklist -> {
                    if (Boolean.TRUE.equals(inBlacklist)) {
                        return unauthorizedResponse(exchange, ResultCode.TOKEN_INVALID);
                    }

                    // 6. 校验通过，注入用户信息到请求头
                    return chain.filter(exchange.mutate().request(
                            mutateRequestWithClaims(request, claims)).build());
                });
    }

    /**
     * 白名单/公开读接口：不强制登录，但若请求携带有效 Access Token 则解析并注入用户头。
     * <p>
     * 用于 /api/ai/chat 等接口：游客可无 Token 访问，登录用户需把 userId 传给下游以写入会话归属。
     * </p>
     */
    private Mono<Void> filterWithOptionalAuth(
            ServerWebExchange exchange,
            GatewayFilterChain chain,
            ServerHttpRequest request) {
        String authHeader = request.getHeaders().getFirst(AuthConstants.TOKEN_HEADER);
        String token = JwtUtil.extractToken(authHeader);
        if (!StringUtils.hasText(token)) {
            return chain.filter(exchange);
        }

        Claims claims;
        try {
            claims = JwtUtil.parseToken(token, jwtProperties.getSecret());
        } catch (Exception e) {
            log.debug("白名单路径 Token 无效，按游客放行: path={}", request.getURI().getPath());
            return chain.filter(exchange);
        }

        if (!JwtUtil.isAccessToken(claims)) {
            return chain.filter(exchange);
        }

        String jti = JwtUtil.getJti(claims);
        String blacklistKey = AuthConstants.REDIS_BLACKLIST_PREFIX + jti;

        return reactiveRedisTemplate.hasKey(blacklistKey)
                .flatMap(inBlacklist -> {
                    if (Boolean.TRUE.equals(inBlacklist)) {
                        return chain.filter(exchange);
                    }
                    return chain.filter(exchange.mutate().request(
                            mutateRequestWithClaims(request, claims)).build());
                });
    }

    /**
     * 将 JWT 载荷写入下游请求头
     */
    private ServerHttpRequest mutateRequestWithClaims(ServerHttpRequest request, Claims claims) {
        Long userId = claims.get(AuthConstants.CLAIM_USER_ID, Long.class);
        String username = claims.get(AuthConstants.CLAIM_USERNAME, String.class);
        @SuppressWarnings("unchecked")
        List<String> roles = claims.get(AuthConstants.CLAIM_ROLES, List.class);
        String rolesHeader = roles != null ? String.join(",", roles) : "";

        return request.mutate()
                .header(AuthConstants.HEADER_USER_ID, String.valueOf(userId))
                .header(AuthConstants.HEADER_USERNAME, username != null ? username : "")
                .header(AuthConstants.HEADER_ROLES, rolesHeader)
                .build();
    }

    /**
     * 判断路径是否匹配白名单
     */
    private boolean isWhitelisted(String path) {
        for (String pattern : whitelistProperties.getWhitelist()) {
            if (pathMatcher.match(pattern, path)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 博客公开读接口免鉴权（GET 请求）
     * <p>
     * /api/blogs、/api/blogs/latest、/api/blogs/categories、/api/blogs/{数字id}
     * 管理端 /api/blogs/admin/** 不在此范围，仍需 JWT + ADMIN。
     * </p>
     */
    private boolean isPublicBlogRead(String path, HttpMethod method) {
        if (!HttpMethod.GET.equals(method)) {
            return false;
        }
        if ("/api/blogs".equals(path) || "/api/blogs/".equals(path)) {
            return true;
        }
        if ("/api/blogs/latest".equals(path) || "/api/blogs/categories".equals(path)) {
            return true;
        }
        if (path.startsWith("/api/blogs/assets/")) {
            return true;
        }
        return path.matches("/api/blogs/\\d+");
    }

    /**
     * 内容服务公开读接口（GET）
     */
    private boolean isPublicContentRead(String path, HttpMethod method) {
        if (!HttpMethod.GET.equals(method)) {
            return false;
        }
        if ("/api/content/home".equals(path)
                || "/api/content/about".equals(path)
                || "/api/content/skills".equals(path)
                || "/api/content/projects".equals(path)) {
            return true;
        }
        return path.matches("/api/content/projects/\\d+");
    }

    /**
     * 文件服务公开读（GET）：头像、封面等静态资源
     */
    private boolean isPublicFileRead(String path, HttpMethod method) {
        if (!HttpMethod.GET.equals(method)) {
            return false;
        }
        return path.startsWith("/api/files/public/");
    }

    /**
     * 返回 401 未授权 JSON 响应
     */
    private Mono<Void> unauthorizedResponse(ServerWebExchange exchange, ResultCode resultCode) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.OK);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);

        Result<Void> result = Result.fail(resultCode);
        byte[] bytes;
        try {
            bytes = objectMapper.writeValueAsString(result).getBytes(StandardCharsets.UTF_8);
        } catch (JsonProcessingException e) {
            bytes = "{\"code\":40103,\"message\":\"未登录\"}".getBytes(StandardCharsets.UTF_8);
        }

        DataBuffer buffer = response.bufferFactory().wrap(bytes);
        return response.writeWith(Mono.just(buffer));
    }

    /**
     * 过滤器优先级：数字越小越先执行
     * -1 确保在路由转发之前完成鉴权
     */
    @Override
    public int getOrder() {
        return -100;
    }
}
