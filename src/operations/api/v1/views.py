from rest_framework import generics, permissions, status
from rest_framework.response import Response

from operations.models import (
    CinemaBranch,
    CinemaBranchImage,
    Hall,
    HallImage,
    Seat,
    Showtime,
    ShowtimeSeat,
)
from .permissions import IsCinemaManager, IsManagerOrBranchAdmin
from .serializers import (
    CinemasBranchRegisterSerializer,
    CinemaBranchListSerializer,
    CinemaBranchDetailSerializers,
    CinemaBranchUpdateSerializer,
    CinemaBranchImageCreateSerializer,
    CinemaBranchImageUpdateSerializer,
    HallRegisterSerializer,
    HallListSerializer,
    HallDetailSerializer,
    HallUpdateSerializer,
    HallImageCreateSerializer,
    HallImageUpdateSerializer,
    SeatSerializer,
    SeatUpdateSerializer,
    SeatBulkCreateSerializer,
    ShowtimeListSerializer,
    ShowtimeDetailSerializer,
    ShowtimeCreateSerializer,
    ShowtimeUpdateSerializer,
    ShowtimeSeatStatusUpdateSerializer,
)

# ==================== CinemaBranch ====================


class CinemaBranchListApiView(generics.ListAPIView):
    serializer_class = CinemaBranchListSerializer
    queryset = CinemaBranch.objects.filter(is_active=True).select_related('address')
    permission_classes = [permissions.AllowAny]
    
    


class CinemaBranchDetailApiView(generics.RetrieveAPIView):
    serializer_class = CinemaBranchDetailSerializers
    queryset= CinemaBranch.objects.select_related('address').prefetch_related('gallery_images')
    permission_classes = [permissions.AllowAny]
    
    
    
    
class CinemaBranchRegisterApiView(generics.GenericAPIView):
    serializer_class = CinemasBranchRegisterSerializer
    permission_classes = [permissions.IsAuthenticated, IsCinemaManager]
    
    
    
    def post(self,request):
        serializer= self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'شعبه با موفقیت ثبت شد', 'data': serializer.data}, status=status.HTTP_201_CREATED)
    
    
class CinemaBranchManageApiView(generics.GenericAPIView):
    serializer_class = CinemaBranchUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = CinemaBranch.objects.select_related('address')
    
    
    def put(self,request,pk):
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj,data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'شعبه با موفقیت بروزرسانی شد'}, status=status.HTTP_200_OK)
    
    def patch(self, request, pk):
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'شعبه با موفقیت بروزرسانی شد'}, status=status.HTTP_200_OK)
    
    
    def delete(self,request,pk):
        if not IsCinemaManager().has_permission(self,request):
            return Response({'detail': 'فقط مدیر سینما مجاز به حذف شعبه است.'}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': 'شعبه غیرفعال شد'}, status=status.HTTP_200_OK)



class CinemaBranchImageCreateApiView(generics.CreateAPIView):
    serializer_class = CinemaBranchImageCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]


class CinemaBranchImageManageApiView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CinemaBranchImageUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = CinemaBranchImage.objects.select_related('branch')
    
    
    
    
#=============== Hall ===========================
class HallListApiView(generics.ListAPIView):
    serializer_class = HallListSerializer
    permission_classes =[permissions.AllowAny]
    
    
    def get_queryset(self):
        queryset = Hall.objects.filter(is_active=True).select_related('branch')
        branch_id = self.request.query_params.get('branch')
        
        if branch_id:
            queryset.filter(branch_id=branch_id)
        return queryset
    
    
    
class HallDetailApiView(generics.RetrieveAPIView):
    serializer_class = HallDetailSerializer
    queryset = Hall.objects.select_related('branch__address').prefetch_related('gallery_images')
    permission_classes = [permissions.IsAuthenticated,IsManagerOrBranchAdmin] 
    
    def post(self,request,pk):
        serializer = self.get_serializer(data=request.data,
                                         context ={'request':request,
                                                   'pk': pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'سالن با موفقیت اضافه شد', 'data': serializer.data}, status=status.HTTP_201_CREATED)
    
    
    



class HallManageApiView(generics.GenericAPIView):
    serializer_class = HallUpdateSerializer
    permission_classes = [permissions.IsAuthenticated,IsManagerOrBranchAdmin]
    queryset = Hall.objects.select_related('branch')
    
    
    
    def put(self,request,pk):
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj,data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'سالن با موفقیت بروزرسانی شد'}, status=status.HTTP_200_OK)
    
    
    
    def patch(self,request,pk):
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj,data = request.data,partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'سالن با موفقیت بروزرسانی شد'}, status=status.HTTP_200_OK)
    
    
    def delete(self, request, pk):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': 'سالن غیرفعال شد'}, status=status.HTTP_200_OK)
    
    
    
class HallImageCreateApiView(generics.CreateAPIView):
    serializer_class = HallImageCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]


class HallImageManageApiView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = HallImageUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = HallImage.objects.select_related('hall__branch')
    
    
    
    
# ======= Seat ==========
class SeatListApiview(generics.ListAPIView):
    serializer_class = SeatSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Seat.objects.filter(hall_id=self.kwargs['hall_pk']).order_by('row_label','seat_number')
    
    
    
class SeatCreateApiView(generics.CreateAPIView):
    serializer_class= SeatSerializer
    permission_classes = [permissions.IsAuthenticated,IsManagerOrBranchAdmin]




class SeatBulkCreateApiView(generics.GenericAPIView):
    serializer_class = SeatBulkCreateSerializer
    permission_classes =[permissions.IsAuthenticated,IsManagerOrBranchAdmin]
    
    
    
    def post(self,request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception = True)
        created_seats = serializer.save()
        return Response(
            {'detail': f'{len(created_seats)} صندلی با موفقیت ثبت شد.'},
            status=status.HTTP_201_CREATED,
        )
        
        
        
class SeatManageApiView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SeatUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = Seat.objects.select_related('hall__branch')
    
    
    
    
    
# ==================== Showtime & ShowtimeSeat ====================
class ShowtimeListApiView(generics.ListAPIView):
    serializer_class = ShowtimeListSerializer
    permission_classes = [permissions.AllowAny]


    def get_queryset(self):
        queryset  = Showtime.objects.select_related('movie','hall__branch').order_by('start_time')
        movie_id = self.request.query_params.get('movie')
        branch_id = self.request.query_params.get('branch')
        hall_id = self.request.query_params.get('hall')
        
        if movie_id:
            queryset = queryset.filter(movie_id=movie_id)
        if branch_id:
            queryset = queryset.filter(hall__branch_id=branch_id)
        if hall_id:
            queryset = queryset.filter(hall_id=hall_id)
        return queryset
    
    
    
    
    
class ShowtimeDetailApiView(generics.RetrieveAPIView):
    serializer_class = ShowtimeDetailSerializer
    queryset = Showtime.objects.select_related('movie','hall__branch').prefetch_related('showtime_seats__seat')
    permission_classes = [permissions.AllowAny]
    
    
    
class ShowtimeCreateApiView(generics.CreateAPIView):
    serializer_class = ShowtimeCreateSerializer
    permission_classes = [permissions.IsAuthenticated,IsManagerOrBranchAdmin]
    
    
    
class ShowtimeManageApiView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ShowtimeUpdateSerializer
    permission_classes = [permissions.IsAuthenticated,IsManagerOrBranchAdmin]
    queryset = Showtime.objects.select_related('hall__branch')
    
    
    
    
class ShowtimeSeatStatusUpdateApiView(generics.UpdateAPIView):
    serializer_class = ShowtimeSeatStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = ShowtimeSeat.objects.select_related('showtime__hall__branch')
    
    
    
    
