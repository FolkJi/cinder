# QSAN REST API 規格文件

本文件定義 QSAN Cinder Driver 與 QSAN Storage 之間的 REST API 介面規格。

---

## 目錄

1. [API 概述](#api-概述)
2. [認證 API](#認證-api)
3. [Volume API](#volume-api)
4. [Snapshot API](#snapshot-api)
5. [Clone API](#clone-api)
6. [Pool API](#pool-api)
7. [iSCSI Target API](#iscsi-target-api)
8. [iSCSI LUN Mapping API](#iscsi-lun-mapping-api)
9. [iSCSI ACL API](#iscsi-acl-api)
10. [iSCSI CHAP API](#iscsi-chap-api)
11. [System API](#system-api)
12. [錯誤處理](#錯誤處理)

---

## API 概述

### Base URL

```
https://{management_ip}:{port}/api
```

預設 port: `443`

### 認證方式

使用 Bearer Token 認證，Token 透過 `/api/login` 取得。

```http
Authorization: Bearer {session_token}
```

### 通用 Headers

```http
Content-Type: application/json
Authorization: Bearer {session_token}
```

### 容量單位

所有容量相關的數值單位為 **bytes**。

---

## 認證 API

### Login

登入並取得 Session Token。

```
POST /api/login
```

#### Request Body

```json
{
  "username": "admin",
  "password": "password123"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| username | string | ✅ | 管理員帳號 |
| password | string | ✅ | 管理員密碼 |

#### Response (200 OK)

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| token | string | Session Token，後續 API 呼叫需帶入 |
| expires_in | integer | Token 有效時間 (秒) |

#### Response (401 Unauthorized)

```json
{
  "error": "Invalid credentials",
  "code": 401
}
```

---

### Logout

登出並清除 Session。

```
POST /api/logout
```

#### Request Headers

```http
Authorization: Bearer {session_token}
```

#### Response (200 OK)

```json
{
  "message": "Logged out successfully"
}
```

---

## Volume API

### Create Volume

建立新的 Volume。

```
POST /api/volumes
```

#### Request Body

```json
{
  "pool": "Pool-1",
  "name": "volume-12345678-1234-1234-1234-123456789abc",
  "size": 10737418240,
  "thin_provision": true
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| pool | string | ✅ | Storage Pool 名稱 |
| name | string | ✅ | Volume 名稱 (Cinder 格式: `volume-{uuid}`) |
| size | integer | ✅ | 容量大小 (bytes) |
| thin_provision | boolean | ❌ | 是否使用 Thin Provisioning (預設: true) |

#### Response (200 OK)

```json
{
  "id": "vol-001",
  "name": "volume-12345678-1234-1234-1234-123456789abc",
  "pool": "Pool-1",
  "size": 10737418240,
  "thin_provision": true,
  "status": "available",
  "created_at": "2024-01-15T10:30:00Z"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | string | Volume 的內部 ID |
| name | string | Volume 名稱 |
| pool | string | 所屬 Pool |
| size | integer | 容量 (bytes) |
| thin_provision | boolean | 是否為 Thin Provisioning |
| status | string | 狀態 |
| created_at | string | 建立時間 (ISO 8601) |

---

### Delete Volume

刪除 Volume。

```
DELETE /api/volumes/{volume_name}
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| volume_name | string | Volume 名稱 |

#### Response (200 OK)

```json
{
  "message": "Volume deleted successfully"
}
```

#### Response (404 Not Found)

```json
{
  "error": "Volume not found",
  "code": 404
}
```

---

### Extend Volume

擴展 Volume 容量。

```
PUT /api/volumes/{volume_name}
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| volume_name | string | Volume 名稱 |

#### Request Body

```json
{
  "size": 21474836480
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| size | integer | ✅ | 新的容量大小 (bytes)，必須大於原始大小 |

#### Response (200 OK)

```json
{
  "id": "vol-001",
  "name": "volume-12345678-1234-1234-1234-123456789abc",
  "size": 21474836480,
  "status": "available"
}
```

---

### Get Volume

查詢 Volume 資訊。

```
GET /api/volumes/{volume_name}
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| volume_name | string | Volume 名稱 |

#### Response (200 OK)

```json
{
  "id": "vol-001",
  "name": "volume-12345678-1234-1234-1234-123456789abc",
  "pool": "Pool-1",
  "size": 10737418240,
  "used_size": 1073741824,
  "thin_provision": true,
  "status": "available",
  "created_at": "2024-01-15T10:30:00Z"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | string | Volume 的內部 ID |
| name | string | Volume 名稱 |
| pool | string | 所屬 Pool |
| size | integer | 容量 (bytes) |
| used_size | integer | 已使用容量 (bytes) |
| thin_provision | boolean | 是否為 Thin Provisioning |
| status | string | 狀態 (available, in-use, error) |
| created_at | string | 建立時間 |

#### Response (404 Not Found)

```json
{
  "error": "Volume not found",
  "code": 404
}
```

---

## Snapshot API

### Create Snapshot

建立 Volume 的 Snapshot。

```
POST /api/volumes/{volume_name}/snapshots
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| volume_name | string | 來源 Volume 名稱 |

#### Request Body

```json
{
  "name": "snapshot-87654321-4321-4321-4321-cba987654321"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| name | string | ✅ | Snapshot 名稱 (Cinder 格式: `snapshot-{uuid}`) |

#### Response (200 OK)

```json
{
  "id": "snap-001",
  "name": "snapshot-87654321-4321-4321-4321-cba987654321",
  "volume_name": "volume-12345678-1234-1234-1234-123456789abc",
  "size": 10737418240,
  "status": "available",
  "created_at": "2024-01-15T11:00:00Z"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | string | Snapshot 的內部 ID |
| name | string | Snapshot 名稱 |
| volume_name | string | 來源 Volume 名稱 |
| size | integer | Snapshot 大小 (bytes) |
| status | string | 狀態 |
| created_at | string | 建立時間 |

---

### Delete Snapshot

刪除 Snapshot。

```
DELETE /api/volumes/{volume_name}/snapshots/{snapshot_name}
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| volume_name | string | 來源 Volume 名稱 |
| snapshot_name | string | Snapshot 名稱 |

#### Response (200 OK)

```json
{
  "message": "Snapshot deleted successfully"
}
```

---

### Get Snapshot

查詢 Snapshot 資訊。

```
GET /api/volumes/{volume_name}/snapshots/{snapshot_name}
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| volume_name | string | 來源 Volume 名稱 |
| snapshot_name | string | Snapshot 名稱 |

#### Response (200 OK)

```json
{
  "id": "snap-001",
  "name": "snapshot-87654321-4321-4321-4321-cba987654321",
  "volume_name": "volume-12345678-1234-1234-1234-123456789abc",
  "size": 10737418240,
  "status": "available",
  "created_at": "2024-01-15T11:00:00Z"
}
```

---

## Clone API

### Clone Volume

從現有 Volume 建立 Clone。

```
POST /api/volumes/{volume_name}/clone
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| volume_name | string | 來源 Volume 名稱 |

#### Request Body

```json
{
  "name": "volume-new-12345678-1234-1234-1234-123456789abc",
  "snapshot": "snapshot-87654321-4321-4321-4321-cba987654321"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| name | string | ✅ | 新 Volume 名稱 |
| snapshot | string | ❌ | 從指定 Snapshot Clone (若不指定則從 Volume 直接 Clone) |

#### Response (200 OK)

```json
{
  "id": "vol-002",
  "name": "volume-new-12345678-1234-1234-1234-123456789abc",
  "pool": "Pool-1",
  "size": 10737418240,
  "source_volume": "volume-12345678-1234-1234-1234-123456789abc",
  "source_snapshot": "snapshot-87654321-4321-4321-4321-cba987654321",
  "status": "available",
  "created_at": "2024-01-15T12:00:00Z"
}
```

---

### Create Volume from Snapshot

從 Snapshot 建立新 Volume。

```
POST /api/volumes/{volume_name}/snapshots/{snapshot_name}/clone
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| volume_name | string | Snapshot 所屬的 Volume 名稱 |
| snapshot_name | string | 來源 Snapshot 名稱 |

#### Request Body

```json
{
  "name": "volume-from-snap-12345678-1234-1234-1234-123456789abc",
  "size": 21474836480
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| name | string | ✅ | 新 Volume 名稱 |
| size | integer | ❌ | 新 Volume 大小 (bytes)，必須 >= Snapshot 大小 |

#### Response (200 OK)

```json
{
  "id": "vol-003",
  "name": "volume-from-snap-12345678-1234-1234-1234-123456789abc",
  "pool": "Pool-1",
  "size": 21474836480,
  "source_snapshot": "snapshot-87654321-4321-4321-4321-cba987654321",
  "status": "available",
  "created_at": "2024-01-15T12:30:00Z"
}
```

---

## Pool API

### Get Pool

查詢 Storage Pool 資訊。

```
GET /api/pools/{pool_name}
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| pool_name | string | Pool 名稱 |

#### Response (200 OK)

```json
{
  "id": "pool-001",
  "name": "Pool-1",
  "total_capacity": 10995116277760,
  "free_capacity": 8796093022208,
  "used_capacity": 2199023255552,
  "status": "healthy",
  "raid_type": "RAID6",
  "disk_count": 8
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | string | Pool 的內部 ID |
| name | string | Pool 名稱 |
| total_capacity | integer | **總容量 (bytes)** ⚠️ 必須回傳 |
| free_capacity | integer | **可用容量 (bytes)** ⚠️ 必須回傳 |
| used_capacity | integer | 已使用容量 (bytes) |
| status | string | 狀態 (healthy, degraded, error) |
| raid_type | string | RAID 類型 |
| disk_count | integer | 磁碟數量 |

> ⚠️ **重要**: `total_capacity` 和 `free_capacity` 是 Cinder Scheduler 計算容量的關鍵欄位，必須正確回傳！

---

## iSCSI Target API

### Create iSCSI Target

建立 iSCSI Target。

```
POST /api/iscsi/targets
```

#### Request Body

```json
{
  "name": "target-12345678-1234-1234-1234-123456789abc",
  "iqn": "iqn.2004-08.com.qsan:target-12345678-1234-1234-1234-123456789abc"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| name | string | ✅ | Target 名稱 (Cinder 格式: `target-{volume_uuid}`) |
| iqn | string | ❌ | 自訂 IQN，若不指定則自動產生 |

#### Response (200 OK)

```json
{
  "id": "target-001",
  "name": "target-12345678-1234-1234-1234-123456789abc",
  "iqn": "iqn.2004-08.com.qsan:target-12345678-1234-1234-1234-123456789abc",
  "status": "online",
  "created_at": "2024-01-15T13:00:00Z"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | string | **Target 的內部 ID** ⚠️ 必須回傳，後續 API 會用到 |
| name | string | Target 名稱 |
| iqn | string | **iSCSI Qualified Name** ⚠️ 必須回傳，Cinder 需要此值 |
| status | string | 狀態 |
| created_at | string | 建立時間 |

---

### Delete iSCSI Target

刪除 iSCSI Target。

```
DELETE /api/iscsi/targets/{target_id}
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| target_id | string | Target ID |

#### Response (200 OK)

```json
{
  "message": "Target deleted successfully"
}
```

---

### Get iSCSI Target

查詢 iSCSI Target 資訊。

```
GET /api/iscsi/targets/{target_id}
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| target_id | string | Target ID |

#### Response (200 OK)

```json
{
  "id": "target-001",
  "name": "target-12345678-1234-1234-1234-123456789abc",
  "iqn": "iqn.2004-08.com.qsan:target-12345678-1234-1234-1234-123456789abc",
  "status": "online",
  "luns": [
    {
      "lun_id": 0,
      "volume": "volume-12345678-1234-1234-1234-123456789abc"
    }
  ],
  "acl": [
    "iqn.1993-08.org.debian:01:604af6a341"
  ]
}
```

---

### Get iSCSI Target by Name

依名稱查詢 iSCSI Target。

```
GET /api/iscsi/targets?name={target_name}
```

#### Query Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| name | string | Target 名稱 |

#### Response (200 OK)

```json
[
  {
    "id": "target-001",
    "name": "target-12345678-1234-1234-1234-123456789abc",
    "iqn": "iqn.2004-08.com.qsan:target-12345678-1234-1234-1234-123456789abc",
    "status": "online"
  }
]
```

> 注意: 回傳為 Array，Driver 會取第一個元素

---

### Get iSCSI Portals

查詢 iSCSI Portal 列表。

```
GET /api/iscsi/portals
```

#### Response (200 OK)

```json
{
  "portals": [
    "192.168.1.101",
    "192.168.1.102"
  ]
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| portals | array[string] | **iSCSI Portal IP 列表** ⚠️ 必須回傳 |

---

## iSCSI LUN Mapping API

### Map Volume to Target

將 Volume 映射到 iSCSI Target。

```
POST /api/iscsi/targets/{target_id}/luns
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| target_id | string | Target ID |

#### Request Body

```json
{
  "volume": "volume-12345678-1234-1234-1234-123456789abc",
  "lun_id": 0
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| volume | string | ✅ | Volume 名稱 |
| lun_id | integer | ❌ | 指定 LUN ID，若不指定則自動分配 |

#### Response (200 OK)

```json
{
  "lun_id": 0,
  "volume": "volume-12345678-1234-1234-1234-123456789abc",
  "target_id": "target-001",
  "status": "mapped"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| lun_id | integer | **LUN ID** ⚠️ 必須回傳，Cinder 需要此值建立 provider_location |
| volume | string | Volume 名稱 |
| target_id | string | Target ID |
| status | string | 狀態 |

---

### Unmap Volume from Target

取消 Volume 與 Target 的映射。

```
DELETE /api/iscsi/targets/{target_id}/luns/{lun_id}
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| target_id | string | Target ID |
| lun_id | integer | LUN ID |

#### Response (200 OK)

```json
{
  "message": "LUN unmapped successfully"
}
```

---

### Get Target LUNs

查詢 Target 的所有 LUN 映射。

```
GET /api/iscsi/targets/{target_id}/luns
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| target_id | string | Target ID |

#### Response (200 OK)

```json
[
  {
    "lun_id": 0,
    "volume": "volume-12345678-1234-1234-1234-123456789abc",
    "size": 10737418240,
    "status": "mapped"
  },
  {
    "lun_id": 1,
    "volume": "volume-87654321-4321-4321-4321-cba987654321",
    "size": 21474836480,
    "status": "mapped"
  }
]
```

---

### Get Volume LUN Mapping

查詢特定 Volume 的 LUN 映射資訊。

```
GET /api/volumes/{volume_name}/mapping
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| volume_name | string | Volume 名稱 |

#### Response (200 OK)

```json
{
  "volume": "volume-12345678-1234-1234-1234-123456789abc",
  "target_id": "target-001",
  "target_iqn": "iqn.2004-08.com.qsan:target-12345678-1234-1234-1234-123456789abc",
  "lun_id": 0
}
```

#### Response (404 Not Found) - 未映射

```json
{
  "error": "Volume is not mapped to any target",
  "code": 404
}
```

---

## iSCSI ACL API

### Add Initiator to Target

將 Initiator 加入 Target 的 ACL。

```
POST /api/iscsi/targets/{target_id}/acl
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| target_id | string | Target ID |

#### Request Body

```json
{
  "initiator": "iqn.1993-08.org.debian:01:604af6a341"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| initiator | string | ✅ | Initiator 的 IQN |

#### Response (200 OK)

```json
{
  "message": "Initiator added to ACL",
  "initiator": "iqn.1993-08.org.debian:01:604af6a341"
}
```

---

### Remove Initiator from Target

從 Target 的 ACL 移除 Initiator。

```
DELETE /api/iscsi/targets/{target_id}/acl/{initiator_iqn}
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| target_id | string | Target ID |
| initiator_iqn | string | Initiator 的 IQN (需 URL encode) |

#### Response (200 OK)

```json
{
  "message": "Initiator removed from ACL"
}
```

---

## iSCSI CHAP API

### Set Target CHAP

設定 Target 的 CHAP 認證。

```
PUT /api/iscsi/targets/{target_id}/chap
```

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| target_id | string | Target ID |

#### Request Body

```json
{
  "username": "chap_user",
  "password": "chap_password_12345"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| username | string | ✅ | CHAP 使用者名稱 |
| password | string | ✅ | CHAP 密碼 (建議長度 12-16 字元) |

#### Response (200 OK)

```json
{
  "message": "CHAP authentication configured",
  "chap_enabled": true
}
```

---

## System API

### Get System Info

查詢系統資訊。

```
GET /api/system
```

#### Response (200 OK)

```json
{
  "model": "XCubeSAN XS5200",
  "serial_number": "QSAN1234567890",
  "version": "5.0.0",
  "iscsi_iqn_prefix": "iqn.2004-08.com.qsan",
  "hostname": "qsan-storage-01",
  "uptime": 864000,
  "status": "healthy"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| model | string | 產品型號 |
| serial_number | string | 序號 |
| version | string | 韌體版本 |
| iscsi_iqn_prefix | string | iSCSI IQN 前綴 |
| hostname | string | 主機名稱 |
| uptime | integer | 運行時間 (秒) |
| status | string | 系統狀態 |

---

## 錯誤處理

### 錯誤回應格式

所有 API 錯誤應回傳以下格式：

```json
{
  "error": "Error message description",
  "code": 400,
  "details": "Additional error details (optional)"
}
```

### HTTP 狀態碼

| 狀態碼 | 說明 |
|--------|------|
| 200 | 成功 |
| 201 | 建立成功 |
| 400 | 請求錯誤 (參數不正確) |
| 401 | 未認證 (Token 無效或過期) |
| 403 | 權限不足 |
| 404 | 資源不存在 |
| 409 | 衝突 (資源已存在或正在使用中) |
| 500 | 伺服器內部錯誤 |

### 常見錯誤範例

#### Volume 不存在

```json
{
  "error": "Volume not found",
  "code": 404,
  "details": "Volume 'volume-12345678' does not exist"
}
```

#### Pool 容量不足

```json
{
  "error": "Insufficient space",
  "code": 400,
  "details": "Pool 'Pool-1' has only 100GB free, requested 500GB"
}
```

#### Volume 正在使用中

```json
{
  "error": "Volume is in use",
  "code": 409,
  "details": "Volume is mapped to an iSCSI target and cannot be deleted"
}
```

---

## Cinder Driver 關鍵回傳值總結

以下是 Cinder Driver 運作時 **必須** 正確回傳的欄位：

| API | 必要欄位 | 用途 |
|-----|---------|------|
| `POST /api/iscsi/targets` | `id`, `iqn` | 建立 iSCSI 連線資訊 |
| `POST /api/iscsi/targets/{id}/luns` | `lun_id` | 建立 provider_location |
| `GET /api/pools/{name}` | `total_capacity`, `free_capacity` | Scheduler 計算可用容量 |
| `GET /api/iscsi/portals` | `portals` | 提供 Multipath 資訊 |

### provider_location 格式

Cinder 會將 iSCSI 連線資訊儲存為 `provider_location`：

```
{portal1}:{port};{portal2}:{port} {iqn} {lun_id}
```

範例：
```
192.168.1.101:3260;192.168.1.102:3260 iqn.2004-08.com.qsan:target-xxx 0
```

---

## Cinder Driver 回傳值規格

本節說明 QSAN Cinder Driver 各方法需要回傳給 Cinder 的資料格式。

> ⚠️ **重要區別**:
> - 前面章節定義的是 **QSAN Storage REST API** 回傳給 `common.py` 的格式
> - 本節定義的是 **Cinder Driver** (`qsan_iscsi.py`) 回傳給 **Cinder Volume Manager** 的格式

---

### do_setup(context)

初始化 Driver，連接到 QSAN Storage。

**回傳值**: `None`

```python
def do_setup(self, context):
    """初始化並登入 QSAN Storage"""
    self.client = QSANClient(...)
    self.client.login()
    # 不需要回傳值
```

---

### check_for_setup_error()

驗證 Driver 設定是否正確。

**回傳值**: `None`

```python
def check_for_setup_error(self):
    """驗證設定"""
    # 驗證 pool 是否存在
    pool_info = self.client.get_pool(self.pool_name)
    if not pool_info:
        raise exception.VolumeBackendAPIException(...)
    # 不需要回傳值
```

---

### get_volume_stats(refresh)

取得 Backend 的容量和功能資訊。

**回傳值**: `dict`

```python
{
    # ===== 必填欄位 =====
    "volume_backend_name": "QSAN_iSCSI",
    "vendor_name": "QSAN",
    "driver_version": "1.0.0",
    "storage_protocol": "iSCSI",
    "total_capacity_gb": 10240.0,        # float, 總容量 (GB)
    "free_capacity_gb": 8192.0,          # float, 可用容量 (GB)

    # ===== 選填欄位 =====
    "reserved_percentage": 0,             # int, 保留百分比
    "location_info": "QSAN:Pool-1",      # string, 位置資訊
    "QoS_support": False,                 # bool, 是否支援 QoS
    "provisioned_capacity_gb": 2048.0,   # float, 已分配容量
    "max_over_subscription_ratio": 20.0, # float, 超額訂閱比例
    "thin_provisioning_support": True,   # bool, 是否支援 Thin Provisioning
    "thick_provisioning_support": False, # bool, 是否支援 Thick Provisioning
    "multiattach": False,                 # bool, 是否支援多重掛載
    "online_extend_support": True,        # bool, 是否支援在線擴展
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| volume_backend_name | string | ✅ | Backend 名稱 (從設定檔取得) |
| vendor_name | string | ✅ | 廠商名稱 |
| driver_version | string | ✅ | Driver 版本 |
| storage_protocol | string | ✅ | 儲存協定 (`"iSCSI"`) |
| total_capacity_gb | float | ✅ | 總容量 (GB)，可用 `"unknown"` 或 `"infinite"` |
| free_capacity_gb | float | ✅ | 可用容量 (GB)，可用 `"unknown"` 或 `"infinite"` |
| thin_provisioning_support | bool | ❌ | 是否支援 Thin Provisioning |
| QoS_support | bool | ❌ | 是否支援 QoS |
| multiattach | bool | ❌ | 是否支援 Multi-attach |

---

### create_volume(volume)

建立 Volume。

**回傳值**: `None` 或 `dict` (model_update)

```python
# 方式 1: 不回傳 (最常見)
def create_volume(self, volume):
    self.client.create_volume(
        pool_name=self.pool_name,
        volume_name=volume.name,
        size_gb=volume.size,
        thin=True
    )
    # 回傳 None

# 方式 2: 回傳 model_update (需要更新 DB 欄位時)
def create_volume(self, volume):
    result = self.client.create_volume(...)
    return {
        "provider_location": "some_location_info",
        "provider_auth": "CHAP user password",
        "metadata": {"key": "value"}
    }
```

| 回傳欄位 | 類型 | 說明 |
|---------|------|------|
| provider_location | string | 儲存位置資訊 (可選) |
| provider_auth | string | 認證資訊 (可選) |
| metadata | dict | 額外 metadata (可選) |

---

### delete_volume(volume)

刪除 Volume。

**回傳值**: `None`

```python
def delete_volume(self, volume):
    self.client.delete_volume(volume.name)
    # 不需要回傳值
```

---

### extend_volume(volume, new_size)

擴展 Volume 容量。

**回傳值**: `None`

```python
def extend_volume(self, volume, new_size):
    """
    :param volume: Volume 物件
    :param new_size: 新容量 (GB, int)
    """
    self.client.extend_volume(volume.name, new_size)
    # 不需要回傳值
```

---

### create_export(context, volume, connector)

建立 iSCSI Export (Target, LUN Mapping)。

**回傳值**: `dict` (model_update)

```python
def create_export(self, context, volume, connector):
    # 建立 iSCSI Target
    target_info = self.client.create_iscsi_target(target_name)
    target_id = target_info['id']
    target_iqn = target_info['iqn']

    # 映射 Volume 到 Target
    lun_info = self.client.map_volume_to_target(volume.name, target_id)
    lun_id = lun_info['lun_id']

    # 取得 Portal 列表
    portals = self.client.get_iscsi_portals()

    # 建立 provider_location
    portal_str = ";".join([f"{p}:3260" for p in portals])
    provider_location = f"{portal_str} {target_iqn} {lun_id}"

    return {
        "provider_location": provider_location,
        "provider_auth": None  # 或 "CHAP username password"
    }
```

| 回傳欄位 | 類型 | 必填 | 說明 |
|---------|------|------|------|
| provider_location | string | ✅ | iSCSI 連線資訊 |
| provider_auth | string | ❌ | CHAP 認證資訊 (格式: `"CHAP username password"`) |

**provider_location 格式**:
```
{portal1}:{port};{portal2}:{port} {target_iqn} {lun_id}
```

範例:
```
192.168.1.101:3260;192.168.1.102:3260 iqn.2004-08.com.qsan:target-xxx 0
```

---

### remove_export(context, volume)

移除 iSCSI Export。

**回傳值**: `None`

```python
def remove_export(self, context, volume):
    # 從 provider_location 解析資訊
    # 取消 LUN Mapping
    # 刪除 iSCSI Target
    # 不需要回傳值
```

---

### initialize_connection(volume, connector)

建立 Initiator 與 Target 的連線。

**回傳值**: `dict` (connection_info)

```python
def initialize_connection(self, volume, connector):
    """
    :param volume: Volume 物件
    :param connector: dict 包含 initiator 資訊
        {
            "initiator": "iqn.1993-08.org.debian:01:604af6a341",
            "host": "compute-node-01",
            "ip": "192.168.1.50",
            "multipath": True,
            ...
        }
    """
    initiator_iqn = connector.get('initiator')

    # 將 initiator 加入 Target ACL
    self.client.add_initiator_to_target(target_id, initiator_iqn)

    # 設定 CHAP (如果啟用)
    if self.chap_enabled:
        self.client.set_target_chap(target_id, chap_user, chap_password)

    return {
        "driver_volume_type": "iscsi",
        "data": {
            "target_discovered": True,
            "target_iqn": "iqn.2004-08.com.qsan:target-xxx",
            "target_portal": "192.168.1.101:3260",
            "target_lun": 0,
            "volume_id": volume.id,

            # Multipath 支援 (選填)
            "target_iqns": [
                "iqn.2004-08.com.qsan:target-xxx",
                "iqn.2004-08.com.qsan:target-xxx"
            ],
            "target_portals": [
                "192.168.1.101:3260",
                "192.168.1.102:3260"
            ],
            "target_luns": [0, 0],

            # CHAP 認證 (選填)
            "auth_method": "CHAP",
            "auth_username": "chap_user",
            "auth_password": "chap_password"
        }
    }
```

**connection_info 結構**:

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| driver_volume_type | string | ✅ | `"iscsi"` |
| data | dict | ✅ | 連線資料 |

**data 內容 (單路徑)**:

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| target_discovered | bool | ✅ | 是否需要 discovery |
| target_iqn | string | ✅ | Target IQN |
| target_portal | string | ✅ | Portal 位址 (格式: `ip:port`) |
| target_lun | int | ✅ | LUN ID |
| volume_id | string | ✅ | Volume ID |

**data 內容 (Multipath, 選填)**:

| 欄位 | 類型 | 說明 |
|------|------|------|
| target_iqns | list[string] | 多個 Target IQN |
| target_portals | list[string] | 多個 Portal 位址 |
| target_luns | list[int] | 對應的 LUN ID |

**data 內容 (CHAP, 選填)**:

| 欄位 | 類型 | 說明 |
|------|------|------|
| auth_method | string | `"CHAP"` |
| auth_username | string | CHAP 使用者名稱 |
| auth_password | string | CHAP 密碼 |

---

### terminate_connection(volume, connector)

中斷 Initiator 與 Target 的連線。

**回傳值**: `None`

```python
def terminate_connection(self, volume, connector):
    """
    :param volume: Volume 物件
    :param connector: dict 包含 initiator 資訊，可能為 None (force detach)
    """
    if connector:
        initiator_iqn = connector.get('initiator')
        # 從 ACL 移除 initiator
        self.client.remove_initiator_from_target(target_id, initiator_iqn)
    else:
        # Force detach: 移除所有 initiator
        pass
    # 不需要回傳值
```

> ⚠️ **注意**: 當 `connector` 為 `None` 時，代表 force detach，應移除所有連線。

---

### create_snapshot(snapshot)

建立 Snapshot。

**回傳值**: `None` 或 `dict` (model_update)

```python
def create_snapshot(self, snapshot):
    """
    :param snapshot: Snapshot 物件
        snapshot.volume_name  # 來源 Volume 名稱
        snapshot.name         # Snapshot 名稱 (snapshot-{uuid})
        snapshot.id           # Snapshot UUID
    """
    self.client.create_snapshot(
        volume_name=snapshot.volume_name,
        snapshot_name=snapshot.name
    )
    # 通常回傳 None

    # 或回傳 model_update
    return {
        "provider_location": "snapshot_location_info"
    }
```

---

### delete_snapshot(snapshot)

刪除 Snapshot。

**回傳值**: `None`

```python
def delete_snapshot(self, snapshot):
    self.client.delete_snapshot(
        volume_name=snapshot.volume_name,
        snapshot_name=snapshot.name
    )
    # 不需要回傳值
```

---

### create_volume_from_snapshot(volume, snapshot)

從 Snapshot 建立新 Volume。

**回傳值**: `None` 或 `dict` (model_update)

```python
def create_volume_from_snapshot(self, volume, snapshot):
    """
    :param volume: 新 Volume 物件
    :param snapshot: 來源 Snapshot 物件
    """
    self.client.create_volume_from_snapshot(
        snapshot_volume_name=snapshot.volume_name,
        snapshot_name=snapshot.name,
        new_volume_name=volume.name,
        size_gb=volume.size  # 可能比 snapshot 大
    )

    # 通常回傳 None
    # 或回傳 model_update
    return {
        "provider_location": "volume_location_info"
    }
```

---

### create_cloned_volume(volume, src_vref)

從現有 Volume 建立 Clone。

**回傳值**: `None` 或 `dict` (model_update)

```python
def create_cloned_volume(self, volume, src_vref):
    """
    :param volume: 新 Volume 物件
    :param src_vref: 來源 Volume 物件
    """
    self.client.clone_volume(
        src_volume_name=src_vref.name,
        dst_volume_name=volume.name
    )

    # 如果新 Volume 較大，需要擴展
    if volume.size > src_vref.size:
        self.client.extend_volume(volume.name, volume.size)

    # 通常回傳 None
```

---

### migrate_volume(context, volume, host)

遷移 Volume 到指定 Host。

**回傳值**: `tuple(bool, dict)`

```python
def migrate_volume(self, context, volume, host):
    """
    :param context: Request context
    :param volume: Volume 物件
    :param host: 目標 host 資訊
        {
            "host": "controller@QSAN_iSCSI#Pool-1",
            "capabilities": {...}
        }
    """
    # 判斷是否可以在 backend 內遷移
    if self._can_migrate(volume, host):
        # 執行 backend 遷移
        self._backend_migrate(volume, host)
        return (True, {})
    else:
        # 無法遷移，由 Cinder 處理 (host-assisted migration)
        return (False, None)
```

| 回傳值 | 說明 |
|--------|------|
| `(True, {})` | 遷移成功，可選擇性回傳 model_update |
| `(True, {"provider_location": "..."})` | 遷移成功，更新 provider_location |
| `(False, None)` | 無法遷移，讓 Cinder 使用 host-assisted migration |

---

### ensure_export(context, volume)

確保 Export 存在 (重啟後重建)。

**回傳值**: `None`

```python
def ensure_export(self, context, volume):
    """確保 iSCSI export 存在"""
    # 通常不需要做任何事，因為 export 已存在於 storage
    pass
```

---

## 回傳值總結表

| 方法 | 回傳類型 | 說明 |
|------|---------|------|
| `do_setup` | `None` | 無回傳值 |
| `check_for_setup_error` | `None` | 無回傳值，失敗時 raise exception |
| `get_volume_stats` | `dict` | Backend 統計資訊 |
| `create_volume` | `None` 或 `dict` | 可選 model_update |
| `delete_volume` | `None` | 無回傳值 |
| `extend_volume` | `None` | 無回傳值 |
| `create_export` | `dict` | `{"provider_location": "...", "provider_auth": "..."}` |
| `remove_export` | `None` | 無回傳值 |
| `initialize_connection` | `dict` | `{"driver_volume_type": "iscsi", "data": {...}}` |
| `terminate_connection` | `None` | 無回傳值 |
| `create_snapshot` | `None` 或 `dict` | 可選 model_update |
| `delete_snapshot` | `None` | 無回傳值 |
| `create_volume_from_snapshot` | `None` 或 `dict` | 可選 model_update |
| `create_cloned_volume` | `None` 或 `dict` | 可選 model_update |
| `migrate_volume` | `tuple(bool, dict)` | `(成功?, model_update)` |
| `ensure_export` | `None` | 無回傳值 |

---

## 資料流程圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Cinder Volume Manager                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 呼叫 Driver 方法
                                    │ (volume 物件, connector dict, etc.)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     QSAN Cinder Driver (qsan_iscsi.py)                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ create_volume(volume)                                            │    │
│  │   → 回傳: None 或 {"provider_location": "..."}                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ initialize_connection(volume, connector)                         │    │
│  │   → 回傳: {"driver_volume_type": "iscsi", "data": {...}}        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ get_volume_stats(refresh)                                        │    │
│  │   → 回傳: {"total_capacity_gb": ..., "free_capacity_gb": ...}   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 呼叫 API Client 方法
                                    │ (volume_name, size_gb, etc.)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       QSANClient (common.py)                             │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ create_volume(pool, name, size)                                  │    │
│  │   → 回傳: {"id": "...", "name": "...", "size": ...}             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ get_pool_stats(pool_name)                                        │    │
│  │   → 回傳: {"total_capacity": ..., "free_capacity": ...}         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ REST API 呼叫
                                    │ (JSON Request/Response)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         QSAN Storage REST API                            │
│                    (本文件前面章節定義的 API 規格)                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

*文件版本: 1.1*
*最後更新: 2024*
