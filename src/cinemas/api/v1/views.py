from .serializers import *
from rest_framework import generics,status,permissions
from rest_framework.response import Response
from cinemas.models import Cinema
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import ProtectedError
from cinemas.recommendations import get_recommended_movies
from rest_framework.views import APIView
from django.db import connection
from cinemas.api.v1.serializers import *
from cinemas.search import search_movies
from .permissions import *
from cinemas.cache import (
    get_cached_movie_detail,
    get_cached_movie_list,
    set_cached_movie_detail,
    set_cached_movie_list,
)
from cinemas.ai_service import ask_movie_assistant

class CinemaRegisterApiView(generics.CreateAPIView):
    """Register a new Cinema tenant along with its Manager account."""
    serializer_class = CinemaRegisterSerializer
    permission_classes = [permissions.AllowAny]

    
    
class CinemaListApiView(generics.ListAPIView):
    """List all registered cinemas."""
    serializer_class = CinemaListSerializer
    queryset = Cinema.objects.all()
    permission_classes = [permissions.AllowAny]
    
    
    
    
class CinemaDetailApiView(generics.RetrieveAPIView):
    """Retrieve full details of a single cinema by primary key."""
    permission_classes = [permissions.AllowAny]
    queryset = Cinema.objects.all()
    serializer_class = CinemaDetailSerializer
    
    
    
class CinemaUpdateApiview(generics.GenericAPIView):
    """Update a cinema's profile details via PUT or PATCH."""
    permission_classes = [permissions.AllowAny]
    queryset = Cinema.objects.all()
    serializer_class = CinemaUpdateSerializer
    
    
    def get_object(self,pk):
        """Return the Cinema matching `pk` or raise 404."""
        return get_object_or_404(Cinema,pk=pk)
    
    
    def put(self,request,pk):
        """Perform a full update of the target cinema."""
        obj = self.get_object(pk)
        serializer = self.get_serializer(instance=obj,data=request.data,context={'request':request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self,request,pk):
        """Perform a partial update of the target cinema."""
        obj = self.get_object(pk)
        serializer = self.get_serializer(instance=obj,data=request.data,context={'request':request},partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
        
        
class CinemaDeleteApiView(generics.GenericAPIView):
    """Delete the cinema owned by the authenticated manager."""
    model = Cinema
    permission_classes = [permissions.IsAuthenticated]
    
    
    def get_object(self):
        """Return the Cinema managed by `request.user` or raise 404."""
        return get_object_or_404(self.model,manager__user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """Delete the manager's cinema and return 204 No Content."""
        cinema = self.get_object()
        cinema.delete()
        return Response(
            {"message": "سینما با موفقیت حذف شد."}, 
            status=status.HTTP_204_NO_CONTENT
        )
        
        
        


class MovieRegisterApiview(generics.GenericAPIView):
    """Create a new movie scoped to the active cinema tenant.

    Restricted to authenticated cinema managers or authorized staff.
    """
    serializer_class = RegisterMovieSerializer
    permission_classes = [permissions.IsAuthenticated,IsCinemaManagerOrStaffForMovie]
    queryset = Movie.objects.all()
    
    
    
    def post(self,request):
        """Validate payload and persist the new movie."""
        serializer = self.get_serializer(data=request.data,context={'request':request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail':'فیلم با موفقیت اضافهه شد'},status=status.HTTP_201_CREATED)
    
    
class MovieListApiView(generics.ListAPIView):
    """List active movies with versioned response caching (`X-Cache: HIT|MISS`)."""
    serializer_class = MovieListSerializer
    queryset = Movie.objects.filter(is_active=True).select_related('created_by_cinema')
    permission_classes = [permissions.AllowAny]
    
    def list(self, request, *args, **kwargs):
        """Return cached movie list when available, otherwise query DB and populate cache."""
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
    """Retrieve a single movie with gallery images and versioned response caching."""
    serializer_class = MovieDetailSerializer
    queryset = Movie.objects.select_related('created_by_cinema').prefetch_related('gallery_images')
    permission_classes = [permissions.AllowAny]
    
    def retrieve(self, request, *args, **kwargs):
        """Return cached movie detail when available, otherwise query DB and populate cache."""
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
    """Update or delete a movie (soft-deactivating if referenced by protected relations)."""
    serializer_class = UpdateMovieSerializer
    permission_classes =[permissions.IsAuthenticated,IsCinemaManagerOrStaffForMovie]
    queryset = Movie.objects.all()
    

    
    
    def put(self,request,pk):
        """Perform a full update on the target movie."""
        obj = self.get_object()
        serializer= self.get_serializer(data=request.data,instance=obj,context={'request':request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail':'فیلم با موفقیت بروز رسانی شد'},status=status.HTTP_200_OK)
    
    
    def patch(self,request,pk):
        """Perform a partial update on the target movie."""
        obj = self.get_object()
        serializer= self.get_serializer(data=request.data,instance=obj,context={'request':request},partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail':'فیلم با موفقیت بروز رسانی شد'},status=status.HTTP_200_OK)
        
    def delete(self, request, pk):
        """Delete the movie or fall back to setting `is_active=False` on ProtectedError."""
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
    """List active movies available for showtimes."""
    serializer_class = MovieListSerializer
    permission_classes = [permissions.AllowAny]
    
    
    queryset = Movie.objects.filter(is_active = True).select_related()
    
    
    
    


class RecommendedMovieListApiView(APIView):
    """Return personalized or popular movie recommendations for the active tenant."""
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
    
    
    
    
class AIMovieAssistantApiView(APIView):
    """Answer natural-language movie discovery prompts using an LLM with local fallback."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Validate the user prompt and return an AI-generated answer with matching movies."""
        serializer = AIMovieAssistantRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = ask_movie_assistant(
            prompt=serializer.validated_data['prompt'],
            schema_name=connection.schema_name,
            limit=serializer.validated_data['limit'],
        )

        movies_data = MovieListSerializer(
            result['movies'],
            many=True,
            context={'request': request},
        ).data

        return Response(
            {
                'provider': result['provider'],
                'answer': result['answer'],
                'count': len(movies_data),
                'recommended_movies': movies_data,
            },
            status=status.HTTP_200_OK,
        )
        
        
        
        
class MovieSearchApiView(APIView):
    """Search active movies via Elasticsearch with automatic PostgreSQL fallback."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Parse query/filter parameters and return matching movies with engine metadata."""
        query = request.query_params.get('q', '').strip()
        genre = request.query_params.get('genre') or None
        min_duration_raw = request.query_params.get('min_duration')
        max_duration_raw = request.query_params.get('max_duration')
        only_showing = request.query_params.get('only_showing', 'false').lower() in ('true', '1', 'yes')

        try:
            min_duration = int(min_duration_raw) if min_duration_raw is not None else None
            max_duration = int(max_duration_raw) if max_duration_raw is not None else None
        except ValueError:
            return Response(
                {'detail': 'مقادیر min_duration و max_duration باید عدد صحیح باشند.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = search_movies(
            query=query,
            genre=genre,
            min_duration=min_duration,
            max_duration=max_duration,
            only_showing=only_showing,
            schema_name=connection.schema_name,
        )

        if isinstance(result, dict):
            movies = result.get('movies', [])
            engine = result.get('engine', 'elasticsearch')
        else:
            movies = result
            engine = 'elasticsearch'

        serializer = MovieListSerializer(movies, many=True, context={'request': request})
        return Response(
            {
                'engine': engine,
                'count': len(serializer.data),
                'results': serializer.data,
            },
            status=status.HTTP_200_OK,
        )