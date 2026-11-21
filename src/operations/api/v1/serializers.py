from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from operations.models import Seat, Address, CinemaBranch, CinemaBranchImage,Hall,HallImage
from .permissions import is_tenant_manager, is_tenant_staff
from django.shortcuts import get_object_or_404




class CinemaAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        
        

class CinemaBranchImageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CinemaBranchImage
        fields = ['id', 'image', 'caption', 'uploaded_at']
        
        


class CinemasBranchRegisterSerializer(serializers.ModelSerializer):
    address = CinemaAddressSerializer()
    class Meta:
        model = CinemaBranch
        fields = '__all__'
        read_only_fileds = ['id','is_active']
        
        
        
    @transaction.atomic
    def create(self, validated_data):
        address_data= validated_data.pop('address')
        branch_admins = validated_data.pop('branch_admins',[])
        address = Address.objects.create(**address_data)
        
        branch = CinemaBranch.objects.create(address =address , **validated_data)
        if branch_admins:
            branch.branch_admins.set(branch_admins)
        return branch
             
             
             
class CinemaBranchDetailSerializers(serializers.ModelSerializer):
    address = CinemaAddressSerializer(read_only=True)
    gallery_images = CinemaBranchImageListSerializer(many=True, read_only=True)

    class Meta:
        model = CinemaBranch
        fields = '__all__'
        
        
        



class CinemaBranchUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CinemaBranch
        fields = ['phone_number', 'branch_name', 'facilities', 'cover_image', 'is_active', 'branch_admins']
        
        




class CinemaBranchImageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CinemaBranchImage
        fields = ['id', 'branch', 'image', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def validate_branch(self, branch):
        request = self.context['request']
        user = request.user
        tenant = request.tenant

       
        is_manager = is_tenant_manager(user, tenant)
        is_branch_admin = (
            is_tenant_staff(user, tenant)
            and branch.branch_admins.filter(id=user.id).exists()
        )

        if not (is_manager or is_branch_admin):
            raise serializers.ValidationError('شما اجازه افزودن تصویر به این شعبه را ندارید.')

        if branch.gallery_images.count() >= 10:
            raise serializers.ValidationError('حداکثر ۱۰ تصویر برای هر شعبه مجاز است.')

        return branch
    
    
    
class CinemaBranchImageUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CinemaBranchImage
        fields = ['id', 'image', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']
        
        
        
        
class CinemaBranchListSerializer(serializers.ModelSerializer):
    city = serializers.CharField(source='address.city', read_only=True)
    province = serializers.CharField(source='address.province', read_only=True)

    class Meta:
        model = CinemaBranch
        fields = ['id', 'branch_name', 'cover_image', 'phone_number', 'city', 'province', 'is_active']
        
        
        
        
class HallImageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = HallImage
        fields = ['id', 'image', 'caption', 'uploaded_at']
        
        
        
        

class HallRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = '__all__'
        read_only_fields = ['id', 'branch', 'is_active']

    def create(self, validated_data):
        branch_pk = self.context['pk']
        branch = get_object_or_404(CinemaBranch, pk=branch_pk)

        request = self.context['request']
        user = request.user
        tenant = request.tenant

        is_manager = is_tenant_manager(user, tenant)
        is_branch_admin = (
            is_tenant_staff(user, tenant)
            and branch.branch_admins.filter(id=user.id).exists()
        )
        if not (is_manager or is_branch_admin):
            raise PermissionDenied('شما اجازه افزودن سالن به این شعبه را ندارید.')

        validated_data['branch'] = branch
        return super().create(validated_data)
    
    
    
class HallListSerializer(serializers.ModelSerializer):
    hall_type_display = serializers.CharField(source='get_hall_type_display', read_only=True)

    class Meta:
        model = Hall
        fields = ['id', 'branch', 'name', 'hall_type', 'hall_type_display', 'image', 'capacity', 'is_active']
        
        
class HallDetailSerializer(serializers.ModelSerializer):
    branch = CinemaBranchListSerializer(read_only=True)
    gallery_images = HallImageListSerializer(many=True, read_only=True)
    hall_type_display = serializers.CharField(source='get_hall_type_display', read_only=True)

    class Meta:
        model = Hall
        fields = '__all__'
        
        
        
class HallUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = ['name', 'hall_type', 'image', 'capacity', 'is_active']
    



class HallImageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HallImage
        fields = ['id', 'hall', 'image', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def validate_hall(self, hall):
        request = self.context['request']
        user = request.user
        tenant = request.tenant

        is_manager = is_tenant_manager(user, tenant)
        is_branch_admin = (
            is_tenant_staff(user, tenant)
            and hall.branch.branch_admins.filter(id=user.id).exists()
        )

        if not (is_manager or is_branch_admin):
            raise serializers.ValidationError('شما اجازه افزودن تصویر به این سالن را ندارید.')

        if hall.gallery_images.count() >= 10:
            raise serializers.ValidationError('حداکثر ۱۰ تصویر برای هر سالن مجاز است.')

        return hall


class HallImageUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HallImage
        fields = ['id', 'image', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']
        
        
        
        


class SeatSerializer(serializers.ModelSerializer):
    class Meta :
        model = Seat
        fields = ['id', 'hall', 'row_label', 'seat_number', 'is_vip']
        read_only_fileds = ['id']
        
        
        
        def validate_hall(self,hall):
            request = self.context['request']
            user = request.user
            tenant = request.tenant
            
            
            is_manager= is_tenant_manager(user,tenant)
            is_branch_admin = (
            is_tenant_staff(user, tenant)
            and hall.branch.branch_admins.filter(id=user.id).exists())
            if not (is_manager or is_branch_admin):
                raise serializers.ValidationError('شما اجازه مدیریت صندلی‌های این سالن را ندارید.')
            return hall
        
        def validate(self, attrs):
            hall = attrs.get('hall') or getattr(self.instance, 'hall', None)
            if self.instance is None and hall and hall.seats.count() >= hall.capacity:
                raise serializers.ValidationError('ظرفیت صندلی‌های این سالن تکمیل شده است.')
            return attrs
        
        
class SeatUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ['id', 'row_label', 'seat_number', 'is_vip']
        read_only_fields = ['id']
        
        
        



class SeatBulkCreateSerializer(serializers.Serializer):
    
    
    hall = serializers.PrimaryKeyRelatedField(queryset=Hall.objects.select_related('branch'))
    rows = serializers.ListField(child=serializers.CharField(max_length=5),help_text='مثلاً ["A", "B", "C"]')
    seats_per_row = serializers.IntegerField(min_value=1)
    vip_rows = serializers.ListField(
        child=serializers.CharField(max_length=5),
        required=False,
        default=list,
        help_text='ردیف‌هایی که VIP هستند، مثلاً ["A", "B"]'
    )
    
    def validate_hall(self, hall):
        request = self.context['request']
        user = request.user
        tenant = request.tenant

        is_manager = is_tenant_manager(user, tenant)
        is_branch_admin = (
            is_tenant_staff(user, tenant)
            and hall.branch.branch_admins.filter(id=user.id).exists()
        )
        if not (is_manager or is_branch_admin):
            raise serializers.ValidationError('شما اجازه افزودن صندلی به این سالن را ندارید.')
        return hall

    def validate(self, attrs):
        hall = attrs['hall']
        total_new_seats = len(attrs['rows']) * attrs['seats_per_row']
        if hall.seats.count() + total_new_seats > hall.capacity:
            raise serializers.ValidationError(
                f'تعداد صندلی‌ها از ظرفیت سالن ({hall.capacity}) بیشتر می‌شود.'
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        hall = validated_data['hall']
        rows = validated_data['rows']
        seats_per_row = validated_data['seats_per_row']
        vip_rows = set(validated_data.get('vip_rows', []))

        seats_to_create = [
            Seat(
                hall=hall,
                row_label=row,
                seat_number=num,
                is_vip=(row in vip_rows),
            )
            for row in rows
            for num in range(1, seats_per_row + 1)
        ]

        return Seat.objects.bulk_create(seats_to_create, ignore_conflicts=True)
    
    
    
    
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from operations.models import Showtime, ShowtimeSeat
from .permissions import is_tenant_manager, is_tenant_staff


class ShowtimeSeatSerializer(serializers.ModelSerializer):
    row_label = serializers.CharField(source='seat.row_label', read_only=True)
    seat_number = serializers.IntegerField(source='seat.seat_number', read_only=True)
    is_vip = serializers.BooleanField(source='seat.is_vip', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ShowtimeSeat
        fields = ['id', 'seat', 'row_label', 'seat_number', 'is_vip', 'status', 'status_display']


class ShowtimeSeatStatusUpdateSerializer(serializers.ModelSerializer):
    """برای تغییر دستی وضعیت صندلی توسط منیجر یا ادمین شعبه (مثلاً فروش حضوری)"""
    class Meta:
        model = ShowtimeSeat
        fields = ['id', 'status']
        read_only_fields = ['id']


class ShowtimeListSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    hall_name = serializers.CharField(source='hall.name', read_only=True)
    branch_name = serializers.CharField(source='hall.branch.branch_name', read_only=True)

    class Meta:
        model = Showtime
        fields = [
            'id', 'movie', 'movie_title', 'hall', 'hall_name',
            'branch_name', 'start_time', 'base_price'
        ]


class ShowtimeDetailSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    hall_name = serializers.CharField(source='hall.name', read_only=True)
    branch_name = serializers.CharField(source='hall.branch.branch_name', read_only=True)
    showtime_seats = ShowtimeSeatSerializer(many=True, read_only=True)

    class Meta:
        model = Showtime
        fields = [
            'id', 'movie', 'movie_title', 'hall', 'hall_name',
            'branch_name', 'start_time', 'base_price', 'showtime_seats'
        ]


class ShowtimeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Showtime
        fields = ['id', 'hall', 'movie', 'start_time', 'base_price']
        read_only_fields = ['id']

    def validate_hall(self, hall):
        request = self.context['request']
        user = request.user
        tenant = request.tenant

        is_manager = is_tenant_manager(user, tenant)
        is_branch_admin = (
            is_tenant_staff(user, tenant)
            and hall.branch.branch_admins.filter(id=user.id).exists()
        )
        if not (is_manager or is_branch_admin):
            raise serializers.ValidationError('شما اجازه ثبت سانس برای این سالن را ندارید.')

        if not hall.is_active:
            raise serializers.ValidationError('این سالن غیرفعال است.')

        if not hall.seats.exists():
            raise serializers.ValidationError('برای این سالن هنوز هیچ صندلی ثبت نشده است.')

        return hall

    def validate_movie(self, movie):
        if not movie.is_active:
            raise serializers.ValidationError('این فیلم غیرفعال است و امکان ثبت سانس ندارد.')
        return movie

    def validate_start_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('زمان شروع سانس باید در آینده باشد.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        showtime = super().create(validated_data)

        seats = showtime.hall.seats.all()
        showtime_seats = [
            ShowtimeSeat(showtime=showtime, seat=seat, status='AVAILABLE')
            for seat in seats
        ]
        ShowtimeSeat.objects.bulk_create(showtime_seats)

        return showtime


class ShowtimeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Showtime

        fields = ['id', 'movie', 'start_time', 'base_price']
        read_only_fields = ['id']

    def validate_movie(self, movie):
        if not movie.is_active:
            raise serializers.ValidationError('این فیلم غیرفعال است.')
        return movie

    def validate_start_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('زمان شروع سانس باید در آینده باشد.')
        return value