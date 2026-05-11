from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

from .models import Department, Position, EmployeeStatusLog
from .serializers import (
    DepartmentSerializer, DepartmentListSerializer,
    PositionSerializer,
    EmployeeListSerializer, EmployeeDetailSerializer,
    EmployeeStatusLogSerializer, BirthdaySerializer
)
from .services import DirectoryService, BirthdayService

User = get_user_model()
directory_service = DirectoryService()
birthday_service = BirthdayService()


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для работы с подразделениями.
    
    list: Получить дерево подразделений
    retrieve: Получить подразделение по ID
    tree: Получить иерархическое дерево
    employees: Получить сотрудников подразделения
    """
    queryset = Department.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return DepartmentListSerializer
        return DepartmentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Фильтр по родителю
        parent = self.request.query_params.get('parent')
        if parent:
            if parent == 'root':
                qs = qs.filter(parent__isnull=True)
            else:
                qs = qs.filter(parent_id=parent)
        
        return qs.order_by('path', 'name')

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Получить полное дерево подразделений"""
        root_id = request.query_params.get('root')
        departments = directory_service.get_department_tree(
            root_id=int(root_id) if root_id else None
        )
        serializer = DepartmentListSerializer(departments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        """Получить сотрудников подразделения"""
        include_children = request.query_params.get('include_children', 'false').lower() == 'true'
        employees = directory_service.get_department_employees(
            department_id=pk,
            include_children=include_children
        )
        serializer = EmployeeListSerializer(employees, many=True)
        return Response(serializer.data)


class PositionViewSet(viewsets.ReadOnlyModelViewSet):
    """API для работы с должностями"""
    queryset = Position.objects.filter(is_active=True)
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Фильтр по подразделению
        department = self.request.query_params.get('department')
        if department:
            qs = qs.filter(department_id=department)
        
        # Фильтр по руководящим должностям
        is_manager = self.request.query_params.get('is_manager')
        if is_manager:
            qs = qs.filter(is_manager=is_manager.lower() == 'true')
        
        return qs.order_by('name')


class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для работы со справочником сотрудников.
    
    list: Поиск сотрудников
    retrieve: Карточка сотрудника
    subordinates: Получить подчинённых
    """
    queryset = User.objects.filter(is_active=True, is_archived=False)
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EmployeeDetailSerializer
        return EmployeeListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Поиск
        query = self.request.query_params.get('q')
        if query:
            employees = directory_service.search_employees(
                query=query,
                department_id=self.request.query_params.get('department'),
                limit=50
            )
            return employees
        
        # Фильтр по подразделению
        department = self.request.query_params.get('department')
        if department:
            qs = qs.filter(department_id=department)
        
        # Фильтр по статусу
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        return qs.select_related('department', 'position').order_by('last_name', 'first_name')

    @action(detail=True, methods=['get'])
    def subordinates(self, request, pk=None):
        """Получить подчинённых сотрудника"""
        direct_only = request.query_params.get('direct_only', 'true').lower() == 'true'
        subordinates = directory_service.get_subordinates(pk, direct_only=direct_only)
        serializer = EmployeeListSerializer(subordinates, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def birthdays(self, request):
        """Получить ближайшие дни рождения"""
        days = int(request.query_params.get('days', 14))
        department_id = request.query_params.get('department')
        
        birthdays = birthday_service.get_upcoming_birthdays(
            days=days,
            department_id=int(department_id) if department_id else None
        )
        
        serializer = BirthdaySerializer(birthdays, many=True)
        return Response(serializer.data)


class EmployeeStatusLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API для журнала статусов сотрудников"""
    queryset = EmployeeStatusLog.objects.all()
    serializer_class = EmployeeStatusLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Фильтр по сотруднику
        employee = self.request.query_params.get('employee')
        if employee:
            qs = qs.filter(employee_id=employee)
        
        # Фильтр по статусу
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        return qs.select_related('employee', 'substitute').order_by('-start_date')


