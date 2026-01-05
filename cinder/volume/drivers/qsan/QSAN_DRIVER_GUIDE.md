# QSAN Cinder Driver 開發指南

本文件說明如何將 QSAN Cinder Driver 加入 OpenStack 官方 Support Matrix，以及 CI 測試的相關資訊。

---

## 目錄

1. [Driver 檔案結構](#driver-檔案結構)
2. [Support Matrix 要求](#support-matrix-要求)
3. [功能支援狀態](#功能支援狀態)
4. [CI 測試架構](#ci-測試架構)
5. [單元測試](#單元測試)
6. [Third Party CI 設定](#third-party-ci-設定)
7. [Gerrit 整合](#gerrit-整合)
8. [相關資源](#相關資源)

---

## Driver 檔案結構

```
cinder/volume/drivers/qsan/
├── __init__.py          # Package 初始化
├── options.py           # 配置選項定義
├── common.py            # REST API 客戶端
└── qsan_iscsi.py        # iSCSI 驅動程式

cinder/tests/unit/volume/drivers/qsan/
├── __init__.py          # 測試 Package 初始化
├── test_qsan_common.py  # API 客戶端單元測試
└── test_qsan_iscsi.py   # iSCSI 驅動程式單元測試
```

---

## Support Matrix 要求

要將 driver 加入官方 Support Matrix，需要滿足以下條件：

| 項目 | 狀態 | 說明 |
|------|------|------|
| Driver Code | ✅ 完成 | 位於 `cinder/volume/drivers/qsan/` |
| Unit Tests | ✅ 完成 | 位於 `cinder/tests/unit/volume/drivers/qsan/` |
| Third Party CI | ❌ 需要架設 | 使用真實硬體執行 Tempest 測試 |
| CI Wiki 頁面 | ❌ 需要建立 | 在 OpenStack Wiki 註冊 CI 資訊 |
| 持續運行 CI | ❌ 需要維護 | CI 必須持續監控所有 Cinder patch |

### 官方文件參考

- [Cinder Driver Support Matrix](https://docs.openstack.org/cinder/latest/reference/support-matrix.html)
- [Adding a Driver to Cinder](https://docs.openstack.org/cinder/latest/contributor/drivers.html)
- [Third Party CI Requirements](https://docs.openstack.org/infra/system-config/third_party.html)

---

## 功能支援狀態

### 目前 QSAN iSCSI Driver 支援的功能

| 功能 | 支援 | 方法 |
|------|------|------|
| Create Volume | ✅ | `create_volume()` |
| Delete Volume | ✅ | `delete_volume()` |
| Attach Volume | ✅ | `initialize_connection()` |
| Detach Volume | ✅ | `terminate_connection()` |
| Extend Volume | ✅ | `extend_volume()` |
| Create Snapshot | ✅ | `create_snapshot()` |
| Delete Snapshot | ✅ | `delete_snapshot()` |
| Create Volume from Snapshot | ✅ | `create_volume_from_snapshot()` |
| Clone Volume | ✅ | `create_cloned_volume()` |
| Volume Migration (host-assisted) | ✅ | `migrate_volume()` (回傳 False) |
| Thin Provisioning | ✅ | 透過 `qsan_thin_provision` 選項 |

### 尚未支援的進階功能

| 功能 | 狀態 | 需要實作的方法 |
|------|------|----------------|
| Extend Attached Volume | ❌ | 需確認 QSAN 支援 online extend |
| QoS | ❌ | `_set_qos()`, 修改 stats |
| Volume Replication | ❌ | `failover_host()`, `failover()` |
| Consistency Group | ❌ | `create_group()`, `delete_group()` 等 |
| Storage-assisted Migration | ❌ | 修改 `migrate_volume()` 回傳 True |
| Multi-Attach | ❌ | 修改 stats 及連線處理 |
| Revert to Snapshot | ❌ | `revert_to_snapshot()` |

---

## CI 測試架構

### 測試類型

```
┌─────────────────────────────────────────────────────────────┐
│                      CI 測試類型                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Unit Tests (單元測試)                                    │
│     ├── 不需要實際硬體                                       │
│     ├── 使用 mock 模擬 API 回應                              │
│     ├── 由 OpenStack 官方 Zuul CI 執行                       │
│     └── 測試程式碼邏輯正確性                                  │
│                                                             │
│  2. Tempest Tests (整合測試)                                 │
│     ├── 需要真實 QSAN 儲存設備                               │
│     ├── 在完整 OpenStack 環境執行                            │
│     ├── 由 Third Party CI (廠商自建) 執行                    │
│     └── 測試實際操作是否成功                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 完整 CI 流程

```
┌─────────────────────────────────────────────────────────────┐
│  開發者提交 Patch 到 Gerrit                                   │
└─────────────────┬───────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  OpenStack 官方 Zuul CI                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • tox -e pep8      → 程式碼風格檢查                  │    │
│  │ • tox -e py3       → Python 3 單元測試              │    │
│  │ • tox -e mypy      → 靜態型別檢查                   │    │
│  │ • 其他 Cinder 相關測試                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────┬───────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  QSAN Third Party CI (需要自行架設)                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 部署 DevStack + QSAN Driver                        │    │
│  │ • 執行 Cinder Tempest 測試                           │    │
│  │ • 使用真實 QSAN 儲存設備                              │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────┬───────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  結果回報到 Gerrit                                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Verified:                                            │    │
│  │   Zuul CI:  +1 ✓                                    │    │
│  │   QSAN CI:  +1 ✓                                    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 單元測試

### 測試檔案說明

#### test_qsan_common.py

測試 REST API 客戶端 (`QSANClient` 類別)：

| 測試類別 | 測試內容 |
|---------|---------|
| Authentication | login, logout |
| Volume Operations | create, delete, extend, get volume |
| Snapshot Operations | create, delete snapshot |
| Clone Operations | clone volume, create from snapshot |
| Pool Operations | get pool, get pool stats |
| iSCSI Operations | create/delete target, map/unmap LUN, ACL, CHAP |
| System Operations | get system info, version |
| Error Handling | retry logic, max retries exceeded |

#### test_qsan_iscsi.py

測試 iSCSI 驅動程式 (`QSANISCSIDriver` 類別)：

| 測試類別 | 測試內容 |
|---------|---------|
| Setup | do_setup, check_for_setup_error |
| Volume Stats | get_volume_stats |
| Volume Operations | create, delete, extend volume |
| iSCSI Export | create_export, remove_export |
| Connection | initialize_connection, terminate_connection |
| Snapshot | create, delete snapshot |
| Clone | create from snapshot, clone volume |
| Migration | migrate_volume |

### 執行單元測試

```bash
# 安裝 tox
pip install tox

# 執行所有 QSAN 測試
tox -e py3 -- cinder.tests.unit.volume.drivers.qsan

# 執行特定測試檔案
tox -e py3 -- cinder.tests.unit.volume.drivers.qsan.test_qsan_iscsi

# 執行特定測試方法
tox -e py3 -- cinder.tests.unit.volume.drivers.qsan.test_qsan_iscsi.QSANISCSIDriverTestCase.test_create_volume

# 檢查程式碼風格
tox -e pep8

# 使用 pytest (如果已安裝)
pytest cinder/tests/unit/volume/drivers/qsan/ -v
```

---

## Third Party CI 設定

### 硬體需求

```
┌────────────────────────────────────────────────────────────────┐
│                     最小硬體需求                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐                                              │
│  │ CI Server    │  • Jenkins / Zuul                            │
│  │              │  • 4 CPU, 8GB RAM, 100GB Disk                │
│  └──────┬───────┘                                              │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐                                              │
│  │ DevStack VM  │  • 可動態建立/銷毀                            │
│  │              │  • 8 CPU, 16GB RAM, 100GB Disk               │
│  └──────┬───────┘                                              │
│         │ iSCSI                                                │
│         ▼                                                      │
│  ┌──────────────┐                                              │
│  │ QSAN Storage │  • 實體儲存設備 或 模擬器                     │
│  │              │  • 至少 1 個 Storage Pool                    │
│  └──────────────┘                                              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Jenkins Pipeline 範例

```groovy
// Jenkinsfile
pipeline {
    agent any

    triggers {
        gerrit(
            triggerOnEvents: [patchsetCreated()],
            serverName: 'OpenStack-Gerrit',
            gerritProjects: [[
                compareType: 'PLAIN',
                pattern: 'openstack/cinder',
                branches: [[ compareType: 'ANT', pattern: '**' ]]
            ]]
        )
    }

    environment {
        QSAN_MGMT_IP = '192.168.1.100'
        QSAN_POOL = 'Pool-1'
    }

    stages {
        stage('Checkout') {
            steps {
                // 下載 Gerrit patch
                sh '''
                    git fetch https://review.opendev.org/openstack/cinder \
                        ${GERRIT_REFSPEC} && git checkout FETCH_HEAD
                '''
            }
        }

        stage('Setup DevStack') {
            steps {
                sh '''
                    # 設定 local.conf
                    cat > local.conf << EOF
                    [[local|localrc]]
                    CINDER_ENABLED_BACKENDS=qsan-iscsi

                    [[post-config|/etc/cinder/cinder.conf]]
                    [qsan-iscsi]
                    volume_driver = cinder.volume.drivers.qsan.qsan_iscsi.QSANISCSIDriver
                    volume_backend_name = qsan-iscsi
                    qsan_management_ip = ${QSAN_MGMT_IP}
                    qsan_pool_name = ${QSAN_POOL}
                    qsan_login = admin
                    qsan_password = password
                    EOF

                    # 執行 DevStack
                    ./stack.sh
                '''
            }
        }

        stage('Run Tempest') {
            steps {
                sh '''
                    # 執行 Cinder Tempest 測試
                    tempest run --regex 'tempest.api.volume' \
                        --concurrency 1
                '''
            }
        }

        stage('Collect Logs') {
            steps {
                // 收集日誌供除錯
                archiveArtifacts artifacts: '/opt/stack/logs/**'
            }
        }
    }

    post {
        success {
            gerritReview labels: [Verified: 1],
                message: "QSAN CI: PASSED\nLogs: ${BUILD_URL}console"
        }
        failure {
            gerritReview labels: [Verified: -1],
                message: "QSAN CI: FAILED\nLogs: ${BUILD_URL}console"
        }
    }
}
```

### DevStack local.conf 範例

```ini
[[local|localrc]]
# 基本設定
ADMIN_PASSWORD=secret
DATABASE_PASSWORD=$ADMIN_PASSWORD
RABBIT_PASSWORD=$ADMIN_PASSWORD
SERVICE_PASSWORD=$ADMIN_PASSWORD

# 啟用 Cinder
enable_service c-api c-sch c-vol

# QSAN Backend
CINDER_ENABLED_BACKENDS=qsan-iscsi

# 安裝 Tempest
enable_plugin tempest https://opendev.org/openstack/tempest

[[post-config|/etc/cinder/cinder.conf]]
[DEFAULT]
enabled_backends = qsan-iscsi
default_volume_type = qsan-iscsi

[qsan-iscsi]
volume_driver = cinder.volume.drivers.qsan.qsan_iscsi.QSANISCSIDriver
volume_backend_name = qsan-iscsi
qsan_management_ip = 192.168.1.100
qsan_management_port = 443
qsan_management_protocol = https
qsan_login = admin
qsan_password = password
qsan_pool_name = Pool-1
qsan_iscsi_portals = 192.168.1.101,192.168.1.102
qsan_ssl_verify = false
qsan_thin_provision = true
```

---

## Gerrit 整合

### 註冊 CI 帳號

1. **建立 Gerrit 帳號**
   ```
   網址: https://review.opendev.org
   帳號名稱建議: qsan-ci
   ```

2. **產生 SSH Key**
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/gerrit_qsan_ci -C "qsan-ci@example.com"
   ```

3. **將 Public Key 加入 Gerrit**
   - 登入 Gerrit → Settings → SSH Keys → Add Key

4. **申請加入 Third-Party CI 群組**
   - 聯繫 OpenStack Infra team
   - 或在 #openstack-infra IRC 頻道詢問

### 監聽 Gerrit Events

```bash
# 使用 SSH 監聽事件串流
ssh -p 29418 qsan-ci@review.opendev.org gerrit stream-events

# 收到的事件範例 (JSON):
{
  "type": "patchset-created",
  "change": {
    "project": "openstack/cinder",
    "branch": "master",
    "number": 123456,
    "subject": "Add new feature"
  },
  "patchSet": {
    "number": 1,
    "ref": "refs/changes/56/123456/1"
  }
}
```

### 回報結果到 Gerrit

#### 使用 REST API

```bash
# 成功 (+1)
curl -X POST \
  -H "Content-Type: application/json" \
  -u "qsan-ci:HTTP_PASSWORD" \
  -d '{
    "labels": {"Verified": 1},
    "message": "QSAN CI: Build PASSED\n\nAll Tempest tests passed.\nLogs: http://ci.qsan.com/logs/123456"
  }' \
  "https://review.opendev.org/a/changes/123456/revisions/current/review"

# 失敗 (-1)
curl -X POST \
  -H "Content-Type: application/json" \
  -u "qsan-ci:HTTP_PASSWORD" \
  -d '{
    "labels": {"Verified": -1},
    "message": "QSAN CI: Build FAILED\n\nFailed tests:\n- tempest.api.volume.test_volumes_actions\n\nLogs: http://ci.qsan.com/logs/123456"
  }' \
  "https://review.opendev.org/a/changes/123456/revisions/current/review"
```

#### 使用 SSH 命令

```bash
# 成功
ssh -p 29418 qsan-ci@review.opendev.org gerrit review \
  --verified +1 \
  --message '"QSAN CI: Build PASSED"' \
  123456,1

# 失敗
ssh -p 29418 qsan-ci@review.opendev.org gerrit review \
  --verified -1 \
  --message '"QSAN CI: Build FAILED"' \
  123456,1
```

### 註冊 CI Wiki 頁面

在 OpenStack Wiki 建立 CI 頁面：

```
網址: https://wiki.openstack.org/wiki/ThirdPartySystems/QSAN_CI

頁面內容範例:
==================================
Name: QSAN CI
Contact: ci-admin@qsan.com
Intent: Test QSAN XCubeSAN iSCSI driver
Method: Jenkins + DevStack + Tempest
Hardware: QSAN XCubeSAN XS5200 series
Logs: http://ci.qsan.com/logs/
Status: Active
==================================
```

---

## 相關資源

### 官方文件

| 資源 | 網址 |
|------|------|
| Cinder Developer Guide | https://docs.openstack.org/cinder/latest/contributor/ |
| Cinder Driver Support Matrix | https://docs.openstack.org/cinder/latest/reference/support-matrix.html |
| Third Party CI Documentation | https://docs.openstack.org/infra/system-config/third_party.html |
| Tempest Testing | https://docs.openstack.org/tempest/latest/ |
| Gerrit REST API | https://review.opendev.org/Documentation/rest-api.html |

### 範例 CI 實作

| 廠商 | 參考資源 |
|------|---------|
| NetApp | https://wiki.openstack.org/wiki/ThirdPartySystems/NetApp_CI |
| Pure Storage | https://wiki.openstack.org/wiki/ThirdPartySystems/Pure_Storage_CI |
| Dell EMC | https://wiki.openstack.org/wiki/ThirdPartySystems/Dell_EMC_Unity_CI |

### 社群資源

| 資源 | 說明 |
|------|------|
| IRC: #openstack-cinder | Cinder 開發討論 |
| IRC: #openstack-infra | CI 相關問題 |
| Mailing List | openstack-discuss@lists.openstack.org |
| Gerrit | https://review.opendev.org (搜尋 project:openstack/cinder) |

---

## 快速開始檢查清單

- [ ] Driver 程式碼完成 (`cinder/volume/drivers/qsan/`)
- [ ] 單元測試完成 (`cinder/tests/unit/volume/drivers/qsan/`)
- [ ] 本地執行 `tox -e pep8` 通過
- [ ] 本地執行 `tox -e py3 -- cinder.tests.unit.volume.drivers.qsan` 通過
- [ ] 準備 CI 硬體環境 (CI Server + DevStack VM + QSAN Storage)
- [ ] 設定 Jenkins/Zuul CI Pipeline
- [ ] 註冊 Gerrit CI 帳號
- [ ] 測試 Gerrit event 監聽
- [ ] 測試結果回報到 Gerrit
- [ ] 在 OpenStack Wiki 建立 CI 頁面
- [ ] 提交 Driver patch 到 Gerrit
- [ ] 聯繫 Cinder core reviewer 進行 code review

---

*文件版本: 1.0*
*最後更新: 2024*
