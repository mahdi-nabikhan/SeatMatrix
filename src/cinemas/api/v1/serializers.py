from rest_framework import serializers
from profiles.models import Manager
from cinemas.models import Cinema,Movie,MovieImage
from profiles.api.v1.manager import serializers as manager_serializer
from django.db import transaction
from rest_framework.exceptions import NotFound



class CinemaRegisterSerializer (serializers.ModelSerializer):
    manager = manager_serializer.ManagerRegisterSerializer()
    class Meta : 
        fields = '__all__'
        model = Cinema
        
    @transaction.atomic
    def create(self, validated_data):
        data = validated_data.pop('manager')
        manager = manager_serializer.ManagerRegisterSerializer().create(data)
        cinema = Cinema.objects.create(manager=manager,**validated_data)
        return cinema
    
    
    
class CinemaListSerializer (serializers.ModelSerializer):
    class Meta:
        model = Cinema
        fields = ['name','image','description','created_at']
        
        
        
        
class CinemaDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cinema
        fields ='__all__'
        
        
    def to_representation(self, instance):
        res =  super().to_representation(instance)
        res['manager'] = manager_serializer.ManagerDetailSerializer(instance.manager).data
        return res
    
    
    
    
class CinemaUpdateSerializer(serializers.ModelSerializer):
        class Meta:
            model = Cinema
            fields = ['name','image','description','created_at']
            read_only_fields = ['created_at']
            
            
            
            



class MovieRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields ="__all__"
        read_only_fields = 'created_at'
        


class ListAndUpdateMovieSerializers(serializers.ModelSerializer):
    class Meta:
        model=Movie
        fields = ['poster','duration_minutes','description','title']
        
        

class MovieImageListSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)

    class Meta:
        model = MovieImage
        fields = ['id', 'movie', 'movie_title', 'image', 'caption', 'uploaded_at']



class RegisterMovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = '__all__'
        read_only_fields = ['created_by_cinema', 'created_at', 'is_active']

    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by_cinema'] = request.tenant
        return super().create(validated_data)
    
class MovieListSerializer(serializers.ModelSerializer):
    created_by_cinema_name = serializers.CharField(
        source='created_by_cinema.name',
        read_only=True
    )
    class Meta:
        class Meta:
            model = Movie
            fields = [
            'id', 'title', 'duration_minutes', 'poster',
            'is_active', 'created_by_cinema', 'created_by_cinema_name', 'created_at']
    
class MovieDetailSerializer(serializers.ModelSerializer):
    created_by_cinema_name = serializers.CharField(
        source='created_by_cinema.name',
        read_only=True
    )
    gallery_images = MovieImageListSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = '__all__'


class UpdateMovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = '__all__'
        read_only_fields = ['id', 'created_by_cinema', 'created_at']


class MovieImageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovieImage
        fields = ['id', 'movie', 'image', 'caption']
        read_only_fields = ['id']


class MovieImageUpdateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = MovieImage
        fields = ['id', 'image', 'caption']
        read_only_fields = ['id']
        
        
        
