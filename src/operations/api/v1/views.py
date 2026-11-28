from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from cinemas.models import Movie
from operations.models import (
    CinemaBranch,
    CinemaBranchImage,
    Hall,
    HallImage,
    Seat,
    Showtime,
    ShowtimeSeat,
)
from profiles.api.v1.admin.serializers import StaffSerializer

from .permissions import IsCinemaManager, IsManagerOrBranchAdmin
from .serializers import (
    ActiveMovieWithShowtimesSerializer,
    BranchAdminRegisterSerializer,
    CinemaBranchDetailSerializers,
    CinemaBranchImageCreateSerializer,
    CinemaBranchImageUpdateSerializer,
    CinemaBranchListSerializer,
    CinemaBranchUpdateSerializer,
    CinemasBranchRegisterSerializer,
    HallImageCreateSerializer,
    HallImageUpdateSerializer,
    HallListSerializer,
    HallRegisterSerializer,
    HallSerializer,
    HallUpdateSerializer,
    SeatBulkCreateSerializer,
    SeatSerializer,
    SeatUpdateSerializer,
    ShowtimeCreateSerializer,
    ShowtimeDetailSerializer,
    ShowtimeListSerializer,
    ShowtimeSeatStatusUpdateSerializer,
    ShowtimeUpdateSerializer,
)


# ==================== CinemaBranch ====================


class CinemaBranchListApiView(generics.ListAPIView):
    """List all active branches belonging to the current cinema tenant."""

    serializer_class = CinemaBranchListSerializer
    queryset = CinemaBranch.objects.filter(is_active=True).select_related('address')
    permission_classes = [permissions.AllowAny]


class CinemaBranchDetailApiView(generics.RetrieveAPIView):
    """Retrieve detailed information for a single CinemaBranch with address and gallery."""

    serializer_class = CinemaBranchDetailSerializers
    queryset = CinemaBranch.objects.select_related('address').prefetch_related('gallery_images')
    permission_classes = [permissions.AllowAny]


class CinemaBranchRegisterApiView(generics.GenericAPIView):
    """Create a new CinemaBranch and its Address under the active tenant.

    Restricted to the tenant's cinema manager (`IsCinemaManager`).
    """

    serializer_class = CinemasBranchRegisterSerializer
    permission_classes = [permissions.IsAuthenticated, IsCinemaManager]

    def post(self, request):
        """Validate branch payload and create a new CinemaBranch."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'شعبه با موفقیت ثبت شد', 'data': serializer.data},
            status=status.HTTP_201_CREATED,
        )


class CinemaBranchManageApiView(generics.GenericAPIView):
    """Update a CinemaBranch (manager or branch admin) or soft-deactivate it (manager only)."""

    serializer_class = CinemaBranchUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = CinemaBranch.objects.select_related('address')

    def put(self, request, pk):
        """Perform a full update of the target CinemaBranch."""
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'شعبه با موفقیت بروزرسانی شد'}, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        """Perform a partial update of the target CinemaBranch."""
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'شعبه با موفقیت بروزرسانی شد'}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        """Soft-deactivate the branch by setting `is_active=False` (cinema manager only)."""
        if not IsCinemaManager().has_permission(request, self):
            return Response(
                {'detail': 'فقط مدیر سینما مجاز به حذف شعبه است.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': 'شعبه غیرفعال شد'}, status=status.HTTP_200_OK)


class CinemaBranchImageCreateApiView(generics.CreateAPIView):
    """Upload a gallery image for a CinemaBranch."""

    serializer_class = CinemaBranchImageCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    parser_classes = [MultiPartParser, FormParser]


class CinemaBranchImageManageApiView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an existing CinemaBranchImage."""

    serializer_class = CinemaBranchImageUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = CinemaBranchImage.objects.select_related('branch')


# ==================== Hall ====================


class HallListApiView(generics.ListAPIView):
    """List active halls in the tenant, optionally filtered by `branch` query parameter."""

    serializer_class = HallListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Return active halls, narrowing by `branch` query param if supplied."""
        queryset = Hall.objects.filter(is_active=True).select_related('branch')
        branch_id = self.request.query_params.get('branch')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        return queryset


class HallRegisterApiView(generics.GenericAPIView):
    """Register a new Hall under a branch identified by URL `pk`."""

    serializer_class = HallRegisterSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]

    def post(self, request, pk):
        """Validate payload and create a Hall linked to the specified branch."""
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request, 'pk': pk},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'سالن با موفقیت اضافه شد', 'data': serializer.data},
            status=status.HTTP_201_CREATED,
        )


class HallManageApiView(generics.GenericAPIView):
    """Update a Hall or soft-deactivate it (`is_active=False`)."""

    serializer_class = HallUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = Hall.objects.select_related('branch')

    def put(self, request, pk):
        """Perform a full update on the target Hall."""
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'سالن با موفقیت بروزرسانی شد'}, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        """Perform a partial update on the target Hall."""
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'سالن با موفقیت بروزرسانی شد'}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        """Soft-deactivate the Hall by setting `is_active=False`."""
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': 'سالن غیرفعال شد'}, status=status.HTTP_200_OK)


class HallImageCreateApiView(generics.CreateAPIView):
    """Upload a gallery image for a Hall."""

    serializer_class = HallImageCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]


class HallImageManageApiView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an existing HallImage."""

    serializer_class = HallImageUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = HallImage.objects.select_related('hall__branch')


class BranchHallListCreateApiView(generics.ListCreateAPIView):
    """List halls for a specific branch or create a new hall under that branch.

    Public users see only active halls; the cinema manager and that branch's admins
    also see inactive halls.
    """

    serializer_class = HallSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_branch(self):
        """Return the CinemaBranch matching `branch_id` or raise 404."""
        return get_object_or_404(CinemaBranch, id=self.kwargs['branch_id'])

    def get_permissions(self):
        """Allow GET publicly and restrict POST to the cinema manager or branch admin."""
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsManagerOrBranchAdmin()]

    def get_queryset(self):
        """Return all branch halls for authorized admins, or active-only for public users."""
        branch = self.get_branch()
        qs = Hall.objects.filter(branch=branch)
        user = self.request.user

        is_manager = IsCinemaManager().has_permission(self.request, self)
        staff_profile = getattr(user, 'staff_profile', None)
        is_this_branch_admin = bool(
            staff_profile
            and staff_profile.is_active
            and branch.branch_admins.filter(id=staff_profile.id).exists()
        )

        if is_manager or is_this_branch_admin:
            return qs
        return qs.filter(is_active=True)

    def perform_create(self, serializer):
        """Verify branch-level object permission before saving the new Hall."""
        branch = self.get_branch()
        self.check_object_permissions(self.request, branch)
        serializer.save(branch=branch)


class HallDetailApiView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a single Hall by `hall_id`.

    GET is public, PUT/PATCH require manager or branch admin, and DELETE is manager-only.
    """

    queryset = Hall.objects.select_related('branch')
    serializer_class = HallSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_url_kwarg = 'hall_id'

    def get_permissions(self):
        """Apply method-based permissions: AllowAny (GET), IsCinemaManager (DELETE), else admin."""
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        if self.request.method == 'DELETE':
            return [IsCinemaManager()]
        return [IsManagerOrBranchAdmin()]


# ==================== Seat ====================


class SeatListApiView(generics.ListAPIView):
    """List all seats for a specific Hall ordered by row label and seat number."""

    serializer_class = SeatSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Return seats belonging to `hall_pk` sorted by row and number."""
        return Seat.objects.filter(hall_id=self.kwargs['hall_pk']).order_by('row_label', 'seat_number')


class SeatCreateApiView(generics.CreateAPIView):
    """Create a single Seat inside a Hall within its capacity limit."""

    serializer_class = SeatSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]


class SeatBulkCreateApiView(generics.GenericAPIView):
    """Bulk-create a matrix of rows and seats (with optional VIP rows) for a Hall."""

    serializer_class = SeatBulkCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]

    def post(self, request):
        """Validate seating layout and bulk-insert the generated Seat records."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created_seats = serializer.save()
        return Response(
            {'detail': f'{len(created_seats)} صندلی با موفقیت ثبت شد.'},
            status=status.HTTP_201_CREATED,
        )


class SeatManageApiView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an individual Seat."""

    serializer_class = SeatUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = Seat.objects.select_related('hall__branch')


# ==================== Showtime & ShowtimeSeat ====================


class ShowtimeListApiView(generics.ListAPIView):
    """List showtimes ordered chronologically with optional movie, branch, and hall filters."""

    serializer_class = ShowtimeListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Return showtimes filtered by `movie`, `branch`, and `hall` query parameters."""
        queryset = Showtime.objects.select_related('movie', 'hall__branch').order_by('start_time')
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
    """Retrieve a Showtime along with its full seat availability map."""

    serializer_class = ShowtimeDetailSerializer
    queryset = Showtime.objects.select_related('movie', 'hall__branch').prefetch_related('showtime_seats__seat')
    permission_classes = [permissions.AllowAny]


class ShowtimeCreateApiView(generics.CreateAPIView):
    """Create a future Showtime and auto-generate AVAILABLE ShowtimeSeat records."""

    serializer_class = ShowtimeCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]


class ShowtimeManageApiView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an existing Showtime."""

    serializer_class = ShowtimeUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = Showtime.objects.select_related('hall__branch')


class ShowtimeSeatStatusUpdateApiView(generics.UpdateAPIView):
    """Manually update a ShowtimeSeat's booking status (e.g., box-office sales)."""

    serializer_class = ShowtimeSeatStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrBranchAdmin]
    queryset = ShowtimeSeat.objects.select_related('showtime__hall__branch')


class ActiveMovieShowTimeListApiView(generics.ListAPIView):
    """List active movies that have at least one upcoming showtime in an active hall/branch."""

    serializer_class = ActiveMovieWithShowtimesSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Return distinct active movies prefetched with their upcoming active showtimes."""
        now = timezone.now()
        upcoming_showtimes = (
            Showtime.objects.filter(
                start_time__gte=now,
                hall__is_active=True,
                hall__branch__is_active=True,
            )
            .select_related('hall__branch')
            .order_by('start_time')
        )
        return (
            Movie.objects.filter(
                is_active=True,
                showtimes__start_time__gte=now,
                showtimes__hall__is_active=True,
                showtimes__hall__branch__is_active=True,
            )
            .prefetch_related(Prefetch('showtimes', queryset=upcoming_showtimes))
            .distinct()
        )


# ==================== Branch Admins ====================


class BranchAdminRegisterApiView(generics.GenericAPIView):
    """Create a new Staff user and assign them as an admin of the target branch."""

    serializer_class = BranchAdminRegisterSerializer
    permission_classes = [IsCinemaManager]

    def post(self, request, branch_id):
        """Validate staff registration payload and attach the staff member to the branch."""
        branch = get_object_or_404(CinemaBranch, id=branch_id)
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request, 'branch': branch},
        )
        serializer.is_valid(raise_exception=True)
        staff = serializer.save()
        return Response(
            {
                'staff_id': staff.id,
                'email': staff.user.email,
                'username': staff.user.username,
                'shift': staff.shift,
                'branch_id': branch.id,
                'branch_name': branch.branch_name,
            },
            status=status.HTTP_201_CREATED,
        )


class BranchAdminListApiView(generics.ListAPIView):
    """List all staff admins assigned to a specific CinemaBranch."""

    serializer_class = StaffSerializer
    permission_classes = [IsCinemaManager]

    def get_queryset(self):
        """Return staff admins linked to `branch_id` with prefetched users."""
        branch = get_object_or_404(CinemaBranch, id=self.kwargs['branch_id'])
        return branch.branch_admins.select_related('user').all()


class BranchAdminRemoveApiView(generics.DestroyAPIView):
    """Remove a staff member from a branch's admin list without deleting the Staff record."""

    permission_classes = [IsCinemaManager]

    def delete(self, request, branch_id, staff_id):
        """Unlink `staff_id` from `branch_id.branch_admins` and return 204."""
        branch = get_object_or_404(CinemaBranch, id=branch_id)
        staff = get_object_or_404(branch.branch_admins, id=staff_id)
        branch.branch_admins.remove(staff)
        return Response(status=status.HTTP_204_NO_CONTENT)