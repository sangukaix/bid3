from pathlib import Path

from django.contrib.auth import authenticate, get_user_model
from pptx import Presentation
from rest_framework import serializers

from .models import CompanyDocument, CompanyProfile, ProjectReferenceDocument


User = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()  # 사용자가 입력한 아이디
    password = serializers.CharField(write_only=True)  # 응답에는 노출하지 않음

    def validate(self, data):
        user = authenticate(
            username=data["username"],
            password=data["password"],
        )

        if user is None:
            raise serializers.ValidationError("아이디 또는 비밀번호가 올바르지 않습니다.")

        data["user"] = user  # 확인된 사용자를 로그인 view에 전달
        return data


class SignupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)  # 로그인에 사용할 아이디
    email = serializers.EmailField()  # 회원 이메일
    password = serializers.CharField(min_length=4, write_only=True)  # 학습용 계정은 최소 4자리 허용
    password_confirm = serializers.CharField(write_only=True)  # 비밀번호 확인용

    def validate_username(self, username):
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError("이미 사용 중인 아이디입니다.")
        return username

    def validate_email(self, email):
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
        return email

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError("비밀번호가 서로 일치하지 않습니다.")
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")  # DB에 저장하지 않는 확인값 제거
        return User.objects.create_user(**validated_data)  # 비밀번호를 암호화해서 회원 생성


class CompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyProfile  # JSON으로 변환할 Django 모델
        fields = [
            "id",
            "company_name",
            "business_registration_number",
            "representative_name",
            "phone",
            "email",
            "website_url_1",
            "website_url_2",
            "established_date",
            "address",
            "industry",
            "related_industries",
            "company_type",
            "employee_count",
            "capital",
            "annual_revenue",
            "main_business",
            "capabilities",
            "licenses",
            "past_performance",
            "required_keywords",
            "preferred_keywords",
            "excluded_keywords",
            "preferred_bid_type",
            "preferred_region",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]  # Django가 자동으로 만드는 값

    def validate_related_industries(self, value):
        industries = list(
            dict.fromkeys(item.strip() for item in value.split(",") if item.strip())
        )
        if len(industries) > 4:
            raise serializers.ValidationError("관련 업종은 최대 4개까지 선택할 수 있습니다.")
        return ", ".join(industries)


def validate_proposal_document_file(uploaded_file):
    allowed_extensions = {".doc", ".docx", ".ppt", ".pptx", ".hwp", ".hwpx"}
    extension = Path(uploaded_file.name).suffix.lower()

    if extension not in allowed_extensions:
        raise serializers.ValidationError(
            "Word, PowerPoint, HWP, HWPX 파일만 업로드할 수 있습니다."
        )
    max_size_mb = 100 if extension == ".pptx" else 20
    if uploaded_file.size > max_size_mb * 1024 * 1024:
        raise serializers.ValidationError(
            f"파일 한 개의 크기는 {max_size_mb}MB를 초과할 수 없습니다."
        )

    if extension == ".pptx":
        try:
            presentation = Presentation(uploaded_file)
            if len(presentation.slides) > 100:
                raise serializers.ValidationError(
                    "PowerPoint 제안서는 최대 100장까지 업로드할 수 있습니다."
                )
        except serializers.ValidationError:
            raise
        except Exception as error:
            raise serializers.ValidationError(
                "올바른 PowerPoint(.pptx) 파일인지 확인해 주세요."
            ) from error
        finally:
            uploaded_file.seek(0)

    return uploaded_file


class CompanyDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = CompanyDocument
        fields = [
            "id",
            "file",
            "original_name",
            "document_type",
            "uploaded_at",
        ]
        read_only_fields = ["id", "original_name", "uploaded_at"]

    def validate_file(self, uploaded_file):
        return validate_proposal_document_file(uploaded_file)


class ProjectReferenceDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = ProjectReferenceDocument
        fields = ["id", "file", "original_name", "processed_at", "uploaded_at"]
        read_only_fields = ["id", "original_name", "processed_at", "uploaded_at"]

    def validate_file(self, uploaded_file):
        return validate_proposal_document_file(uploaded_file)
