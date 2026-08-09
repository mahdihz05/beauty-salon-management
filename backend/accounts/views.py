from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from core.audit import record_audit

from .models import User
from .permissions import HasAnyRole
from .serializers import LogoutSerializer, OTPRequestSerializer, OTPVerifySerializer, UserSerializer
from .services import request_otp, verify_otp


class PlatformUserDirectoryView(ListAPIView):
    serializer_class = UserSerializer
    permission_classes = (HasAnyRole,)
    allowed_roles = (User.Role.ADMIN, User.Role.SUPPORT)
    search_fields = ("phone", "name")
    filterset_fields = ("role", "is_active")
    ordering_fields = ("created_at", "name")
    ordering = ("-created_at",)
    queryset = User.objects.select_related("customer_profile")


class OTPRequestView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = OTPRequestSerializer

    @extend_schema(request=OTPRequestSerializer)
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dispatch = request_otp(phone=serializer.validated_data["phone"], request=request)
        payload = {
            "detail": "کد ورود ارسال شد.",
            "expires_at": dispatch.challenge.expires_at,
        }
        if dispatch.debug_code:
            payload["debug_code"] = dispatch.debug_code
        return Response(payload, status=status.HTTP_201_CREATED)


class OTPVerifyView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = OTPVerifySerializer

    @extend_schema(request=OTPVerifySerializer, responses=UserSerializer)
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, created = verify_otp(**serializer.validated_data)
        refresh = RefreshToken.for_user(user)
        record_audit(
            request=request,
            actor=user,
            action="auth.otp_verified",
            target=user,
            metadata={"new_user": created},
        )
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user, context={"request": request}).data,
                "is_new_user": created,
            }
        )


class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(request=LogoutSerializer)
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return Response(
                {"detail": "توکن تازه‌سازی معتبر نیست."}, status=status.HTTP_400_BAD_REQUEST
            )
        record_audit(request=request, actor=request.user, action="auth.logout", target=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        user = serializer.save()
        record_audit(
            request=self.request, actor=self.request.user, action="profile.updated", target=user
        )
