from .serializers import *
from rest_framework import generics,status,permissions
from rest_framework.response import Response
from cinemas.models import Cinema
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from cinemas.api.v1.serializers import *
from .permissions import *


class CinemaRegisterApiView(generics.CreateAPIView):
    serializer_class = CinemaRegisterSerializer
    permission_classes = [permissions.AllowAny]

    
    
class CinemaListApiView(generics.ListAPIView):
    serializer_class = CinemaListSerializer
    queryset = Cinema.objects.all()
    permission_classes = [permissions.AllowAny]
    
    
    
    
class CinemaDetailApiView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    queryset = Cinema.objects.all()
    serializer_class = CinemaDetailSerializer
    
    
    
class CinemaUpdateApiview(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    queryset = Cinema.objects.all()
    serializer_class = CinemaUpdateSerializer
    
    
    def get_object(self,pk):
        return get_object_or_404(Cinema,pk=pk)
    
    
    def put(self,request,pk):
        obj = self.get_object(pk)
        serializer = self.get_serializer(instance=obj,data=request.data,context={'request':request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self,request,pk):
        obj = self.get_object(pk)
        serializer = self.get_serializer(instance=obj,data=request.data,context={'request':request},partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
        
        
class CinemaDeleteApiView(generics.GenericAPIView):
    model = Cinema
    permission_classes = [permissions.IsAuthenticated]
    
    
    def get_object(self):
        return get_object_or_404(self.model,manager__user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        cinema = self.get_object()
        cinema.delete()
        return Response(
            {"message": "سینما با موفقیت حذف شد."}, 
            status=status.HTTP_204_NO_CONTENT
        )
        
        
        


class MovieRegisterApiview(generics.GenericAPIView):
    serializer_class = RegisterMovieSerializer
    permission_classes = [permissions.IsAuthenticated,IsCinemaManagerOrStaffForMovie]
    queryset = Movie.objects.all()
    
    
    
    def post(self,request):
        serializer = self.get_serializer(data=request.data,context={'request':request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail':'فیلم با موفقیت اضافهه شد'},status=status.HTTP_201_CREATED)
    
    
class MovieListApiView(generics.ListAPIView):
    serializer_class = MovieListSerializer
    queryset = Movie.objects.filter(is_active=True).select_related('created_by_cinema')
    permission_classes = [permissions.AllowAny]
    


class MovieDetailApiview(generics.RetrieveAPIView):
    serializer_class = MovieDetailSerializer
    queryset = Movie.objects.select_related('created_by_cinema').prefetch_related('gallery_images')
    permission_classes = [permissions.AllowAny]
    
    
    
    
class MovieUpdateAndDeleteApiView(generics.GenericAPIView):
    serializer_class = UpdateMovieSerializer
    permission_classes =[permissions.IsAuthenticated,IsCinemaManagerOrStaffForMovie]
    queryset = Movie.objects.all()
    

    
    
    def put(self,request,pk):
        obj = self.get_object()
        serializer= self.get_serializer(data=request.data,instance=obj,context={'request':request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail':'فیلم با موفقیت بروز رسانی شد'},status=status.HTTP_200_OK)
    
    
    def patch(self,request,pk):
        obj = self.get_object()
        serializer= self.get_serializer(data=request.data,instance=obj,context={'request':request},partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail':'فیلم با موفقیت بروز رسانی شد'},status=status.HTTP_200_OK)
        
    def delete(self, request, pk):
        obj = self.get_object()
        try:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            obj.is_active = False
            obj.save(update_fields=['is_active'])
            return Response(
                {'detail': 'این فیلم در سانس‌ها استفاده شده است؛ بنابراین غیرفعال شد.'},
                status=status.HTTP_200_OK,
            )