from django.core.management.base import BaseCommand

from accounts.services import ensure_default_admin


class Command(BaseCommand):
    help = "기본 관리자 계정(이름=관리자 / 사번=ADM001)이 없으면 생성한다."

    def handle(self, *args, **options):
        if ensure_default_admin():
            self.stdout.write(
                self.style.SUCCESS("기본 관리자 계정 생성: 이름=관리자 / 사번=ADM001")
            )
        else:
            self.stdout.write("기본 관리자 계정이 이미 존재합니다. 변경하지 않습니다.")
