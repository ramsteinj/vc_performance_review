import sys
import warnings

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        if 'runserver' not in sys.argv:
            return
        self.ensure_default_admin()

    def ensure_default_admin(self):
        from django.contrib.auth import get_user_model
        from django.db.utils import OperationalError, ProgrammingError

        User = get_user_model()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                if User.objects.filter(employee_number='ADM001').exists():
                    return
                User.objects.create_user(
                    username='ADM001',
                    employee_number='ADM001',
                    name='관리자',
                    password='admin1234!',
                    role=User.Role.ADMIN,
                )
            print(
                '기본 관리자 계정 생성: 이름=관리자 / 사번=ADM001 / 비밀번호=admin1234!'
            )
        except (OperationalError, ProgrammingError):
            print(
                '[accounts] 기본 관리자 계정 생성 실패 - '
                '먼저 python manage.py migrate를 실행하세요'
            )
