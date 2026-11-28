from .serializers import *
from rest_framework import generics,status,permissions
from rest_framework.response import Response
from cinemas.models import Cinema
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from cinemas.recommendations import get_recommended_movies
from rest_framework.views import APIView
from django.db import connection
from cinemas.api.v1.serializers import *
from .permissions import *
from cinemas.cache import (
    get_cached_movie_detail,
    get_cached_movie_list,
    set_cached_movie_detail,
    set_cached_movie_list,
)

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
    def list(self, request, *args, **kwargs):
        host = request.get_host()
        full_path = request.get_full_path()

        cached_data = get_cached_movie_list(host=host, full_path=full_path)
        if cached_data is not None:
            response = Response(cached_data, status=status.HTTP_200_OK)
            response['X-Cache'] = 'HIT'
            return response

        response = super().list(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            set_cached_movie_list(host=host, full_path=full_path, data=response.data)
        response['X-Cache'] = 'MISS'
        return response    


class MovieDetailApiview(generics.RetrieveAPIView):
    serializer_class = MovieDetailSerializer
    queryset = Movie.objects.select_related('created_by_cinema').prefetch_related('gallery_images')
    permission_classes = [permissions.AllowAny]
    
    def retrieve(self, request, *args, **kwargs):
        movie_id = int(kwargs['pk'])
        host = request.get_host()

        cached_data = get_cached_movie_detail(movie_id=movie_id, host=host)
        if cached_data is not None:
            response = Response(cached_data, status=status.HTTP_200_OK)
            response['X-Cache'] = 'HIT'
            return response

        response = super().retrieve(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            set_cached_movie_detail(movie_id=movie_id, host=host, data=response.data)
        response['X-Cache'] = 'MISS'
        return response
    
    
    
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
            
            
            


class ActiveMovieShowTimeListApiView(generics.ListAPIView):
    serializer_class = MovieListSerializer
    permission_classes = [permissions.AllowAny]
    
    
    queryset = Movie.objects.filter(is_active = True).select_related()
    
    
    
    


class RecommendedMovieListApiView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            limit = 10
        limit = max(1, min(limit, 20))

        rec = get_recommended_movies(
            user=request.user,
            schema_name=connection.schema_name,
            limit=limit,
        )

        serialized = MovieListSerializer(
            rec['movies'],
            many=True,
            context={'request': request},
        ).data

        for item in serialized:
            mid = item['id']
            item['recommendation_score'] = rec['scores'].get(mid, 0.0)
            item['recommendation_reason'] = rec['reasons'].get(mid, '')

        response = Response(
            {
                'strategy': rec['strategy'],
                'count': len(serialized),
                'results': serialized,
            },
            status=status.HTTP_200_OK,
        )
        response['X-Cache'] = 'HIT' if rec['cache_hit'] else 'MISS'
        return response