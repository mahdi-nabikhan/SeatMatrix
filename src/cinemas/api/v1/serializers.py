from rest_framework import serializers
from profiles.models import Manager
from cinemas.models import Cinema,Movie,MovieImage
from profiles.api.v1.manager import serializers as manager_serializer
from django.db import transaction
from rest_framework.exceptions import NotFound



class CinemaRegisterSerializer (serializers.ModelSerializer):
    """Atomically register a new Cinema tenant along with its Manager account."""
    manager = manager_serializer.ManagerRegisterSerializer()
    class Meta : 
        fields = '__all__'
        model = Cinema
        
    @transaction.atomic
    def create(self, validated_data):
        """Create the Manager profile first, then provision the Cinema tenant."""
        data = validated_data.pop('manager')
        manager = manager_serializer.ManagerRegisterSerializer().create(data)
        cinema = Cinema.objects.create(manager=manager,**validated_data)
        return cinema
    
    
    
class CinemaListSerializer (serializers.ModelSerializer):
    """Expose summary fields for listing registered cinemas."""
    class Meta:
        model = Cinema
        fields = ['name','image','description','created_at']
        
        
        
        
class CinemaDetailSerializer(serializers.ModelSerializer):
    """Serialize full Cinema details including nested Manager information."""
    class Meta:
        model = Cinema
        fields ='__all__'
        
        
    def to_representation(self, instance):
        """Expand the manager foreign key into serialized manager details when present."""
        res = super().to_representation(instance)
        res['manager'] = (
            manager_serializer.ManagerDetailSerializer(instance.manager).data
            if instance.manager
            else None
        )
        return res
    
    
    
    
class CinemaUpdateSerializer(serializers.ModelSerializer):
        """Allow updating mutable descriptive fields on a Cinema."""
    
        class Meta:
            model = Cinema
            fields = ['name','image','description','created_at']
            read_only_fields = ['created_at']
            
            
            
    
        

class MovieImageListSerializer(serializers.ModelSerializer):
    """Serialize movie gallery image metadata along with the parent movie title."""
    movie_title = serializers.CharField(source='movie.title', read_only=True)

    class Meta:
        model = MovieImage
        fields = ['id', 'movie', 'movie_title', 'image', 'caption', 'uploaded_at']



class RegisterMovieSerializer(serializers.ModelSerializer):
    """Create a Movie and automatically bind `created_by_cinema` to `request.tenant`."""
    class Meta:
        model = Movie
        fields = '__all__'
        read_only_fields = ['created_by_cinema', 'created_at', 'is_active']

    def create(self, validated_data):
        """Assign the active tenant as the movie creator before saving."""
        request = self.context['request']
        validated_data['created_by_cinema'] = request.tenant
        return super().create(validated_data)
    
class MovieListSerializer(serializers.ModelSerializer):
    """Serialize compact movie cards for catalog, search, and recommendation lists."""
    created_by_cinema_name = serializers.CharField(
        source='created_by_cinema.name',
        read_only=True
    )
    genre_display = serializers.CharField(source='get_genre_display', read_only=True)
    class Meta:
            model = Movie
            fields = [
            'id', 'title', 'duration_minutes', 'poster',
            'is_active', 'created_by_cinema', 'created_by_cinema_name', 'created_at','genre_display']
    
class MovieDetailSerializer(serializers.ModelSerializer):
    """Serialize complete movie details including its gallery images."""
    created_by_cinema_name = serializers.CharField(
        source='created_by_cinema.name',
        read_only=True
    )
    gallery_images = MovieImageListSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = '__all__'


class UpdateMovieSerializer(serializers.ModelSerializer):
    """Validate full or partial updates to an existing Movie."""
    class Meta:
        model = Movie
        fields = '__all__'
        read_only_fields = ['id', 'created_by_cinema', 'created_at']


class MovieImageCreateSerializer(serializers.ModelSerializer):
    """Validate creation of a new MovieImage gallery item."""
    class Meta:
        model = MovieImage
        fields = ['id', 'movie', 'image', 'caption']
        read_only_fields = ['id']


class MovieImageUpdateSerializer(serializers.ModelSerializer):
    """Validate updates to an existing MovieImage's file or caption."""
    image = serializers.ImageField(required=False)

    class Meta:
        model = MovieImage
        fields = ['id', 'image', 'caption']
        read_only_fields = ['id']
        
        
        

class AIMovieAssistantRequestSerializer(serializers.Serializer):
    """Validate input prompt and result limit for the AI movie assistant endpoint."""
    prompt = serializers.CharField(min_length=3, max_length=500)
    limit = serializers.IntegerField(min_value=1, max_value=10, required=False, default=3)