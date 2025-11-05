# WODFIT-ML

## Deployment pipeline

이 저장소에는 GitHub Actions를 사용해 애플리케이션을 Amazon EC2 인스턴스에 배포하는 CI/CD 파이프라인이 포함되어 있습니다. 워크플로 파일은 [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)에 있으며 `main` 브랜치에 푸시되거나 수동으로 실행(`workflow_dispatch`)될 때 동작합니다.

### 사전 준비

EC2 인스턴스에 다음 패키지가 설치되어 있어야 합니다.

- `python3` 및 `python3-venv`
- `tar`
- (선택) `systemd` – 서비스 재시작을 자동화하려면 필요합니다.

또한 레포지토리를 배포할 디렉터리(예: `/opt/wodfit-ml`)를 만들어 두고, 애플리케이션을 구동하는 서비스가 있다면 systemd 서비스 이름을 파악합니다.

### GitHub Secrets 설정

워크플로가 동작하려면 다음 GitHub Secrets를 저장소 또는 조직 레벨에 추가해야 합니다.

| Secret 이름 | 설명 |
|-------------|------|
| `EC2_HOST` | 배포 대상 EC2 인스턴스의 도메인 또는 IP 주소 |
| `EC2_USER` | SSH 접속에 사용할 사용자 이름 |
| `EC2_SSH_KEY` | `EC2_USER`가 EC2에 접속할 때 사용하는 **개인키** |
| `EC2_TARGET_DIR` | 애플리케이션을 배포할 서버상의 절대경로 |
| `EC2_SERVICE_NAME` | (선택) 배포 후 재시작할 systemd 서비스 이름 |

SSH 개인키는 PEM 형식의 문자열이어야 하며, 공개키가 EC2 인스턴스의 `~/.ssh/authorized_keys`에 등록되어 있어야 합니다.

### 워크플로가 수행하는 작업

1. 코드를 체크아웃하고 Python 3.10 환경을 준비합니다.
2. `requirements.txt`의 의존성을 설치한 후 `python -m compileall src` 명령으로 소스가 정상적으로 컴파일되는지 확인합니다.
3. 배포 단계에서는 저장소 파일을 아카이브로 묶어 EC2에 전송합니다.
4. EC2 인스턴스에서는 지정한 경로에 아카이브를 풀고, 가상환경(`.venv`)을 생성하여 의존성을 설치합니다.
5. `EC2_SERVICE_NAME`이 설정되어 있으면 해당 systemd 서비스를 재시작합니다.

필요에 따라 워크플로 파일을 수정해 데이터베이스 마이그레이션이나 애플리케이션 시작 명령 등을 추가할 수 있습니다.

## Redis 기반 추론 결과 캐싱

동일한 WOD 입력에 대한 추론 결과를 빠르게 반환하기 위해 Redis 캐시를 사용할 수 있습니다. 애플리케이션이 실행되는 환경에 Redis 인스턴스가 있다면 다음 환경 변수를 설정해 연결 정보를 제공하세요.

| 환경 변수 | 설명 |
|-----------|------|
| `REDIS_URL` | `redis://[:password@]host:port/db` 형식의 연결 문자열. 설정하지 않으면 캐싱 없이 동작합니다. |
| `WOD_CLUSTER_CACHE_TTL` | (선택) 캐시된 추론 결과의 TTL(초 단위). 기본값은 `3600`초입니다. |

캐시 서버에 접속할 수 없거나 오류가 발생하면 애플리케이션은 자동으로 캐시를 건너뛰고 기존 방식대로 추론을 수행합니다.
