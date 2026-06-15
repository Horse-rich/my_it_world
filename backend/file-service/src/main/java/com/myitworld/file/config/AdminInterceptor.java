package com.myitworld.file.config;

import com.myitworld.common.constant.AuthConstants;
import com.myitworld.common.exception.BusinessException;
import com.myitworld.common.result.ResultCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * 上传/删除接口需 ADMIN 角色（Gateway 已校验 JWT 并注入 X-Roles）
 */
@Component
public class AdminInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String roles = request.getHeader(AuthConstants.HEADER_ROLES);
        if (roles == null || !roles.contains(AuthConstants.ROLE_ADMIN)) {
            throw new BusinessException(ResultCode.FORBIDDEN, "需要管理员权限");
        }
        return true;
    }
}
