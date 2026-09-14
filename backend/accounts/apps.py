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
        from django.db.utils import OperationalError, ProgrammingError

        from .services import ensure_default_admin

        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                if ensure_default_admin():
                    print('기본 관리자 계정 생성: 이름=관리자 / 사번=ADM001')
        except (OperationalError, ProgrammingError):
            print(
                '[accounts] 기본 관리자 계정 생성 실패 - '
                '먼저 python manage.py migrate를 실행하세요'
            )
