from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import InAppNotification
from .serializers import InAppNotificationSerializer


class MyNotificationListApiView(generics.ListAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = InAppNotificationSerializer

    def get_queryset(self):
        return InAppNotification.objects.filter(user=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        unread_count = queryset.filter(is_read=False).count()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'unread_count': unread_count,
            'results': serializer.data,
        })


class MarkNotificationReadApiView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        notif = get_object_or_404(InAppNotification, pk=pk, user=request.user)
        if not notif.is_read:
            notif.is_read = True
            notif.save(update_fields=['is_read'])
        return Response(InAppNotificationSerializer(notif).data, status=status.HTTP_200_OK)