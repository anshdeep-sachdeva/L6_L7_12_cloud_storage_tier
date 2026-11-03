import pytest
from cloud_storage_tier import process_storage_tenants, monitor_replication_latency

# Example test case:
def test_single_active_hot_tenant():
    tenants = [
        {
            "account_active": True,
            "tier": "hot",
            "has_backup_vault": False,
            "buckets": [{"size_gb": 100, "corrupted": False, "egress_gb": 50}]
        }
    ]
    result = process_storage_tenants(tenants, 10.0)
    assert result["total_billed"] == 2.5
    assert result["status"] == "BILLED"

# TODO: Add test cases to achieve 90-100% on both Line and Branch coverage!
def test_empty_tenants():
    result = process_storage_tenants([], 10)
    assert result == {"total_billed": 0.0, "status": "ZERO_USAGE"}

def test_negative_support_fee():
    with pytest.raises(ValueError):
        process_storage_tenants([], -1)

def test_inactive_tenant():
    tenants = [{"account_active": False}]
    result = process_storage_tenants(tenants, 10)
    assert result["status"] == "ZERO_USAGE"

def test_cool_tier():
    tenants = [{
        "account_active": True,
        "tier": "cool",
        "buckets": [{"size_gb": 100}],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result == {"total_billed": 1.5, "status": "BILLED"}

def test_archive_tier():
    tenants = [{
        "account_active": True,
        "tier": "archive",
        "buckets": [{"size_gb": 100}],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result == {"total_billed": 0.5, "status": "BILLED"}

def test_unknown_tier():
    tenants = [{"account_active": True, "tier": "unknown"}]
    result = process_storage_tenants(tenants, 10)
    assert result["status"] == "ZERO_USAGE"


def test_zero_bucket_size():
    tenants = [{
        "account_active": True,
        "buckets": [{"size_gb": 0}],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result["total_billed"] == 0.0

def test_negative_bucket_size():
    tenants = [{
        "account_active": True,
        "buckets": [{"size_gb": -10}],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result["total_billed"] == 0.0


def test_corrupted_hot_bucket():
    tenants = [{
        "account_active": True,
        "tier": "hot",
        "buckets": [{"size_gb": 100, "corrupted": True}],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result["total_billed"] == 0.0

def test_corrupted_archive_bucket():
    tenants = [{
        "account_active": True,
        "tier": "archive",
        "buckets": [
            {"size_gb": 100},
            {"size_gb": 100, "corrupted": True},
            {"size_gb": 200},
        ],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result["total_billed"] == 0.0


def test_exactly_500_gb():
    tenants = [{
        "account_active": True,
        "buckets": [{"size_gb": 500}],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result["total_billed"] == 12.5


def test_large_bucket_discount():
    tenants = [{
        "account_active": True,
        "buckets": [{"size_gb": 600}],
    }]
    result = process_storage_tenants(tenants, 10)
    # 600 * 0.025 * 0.90
    assert result["total_billed"] == 13.5

def test_exactly_100_gb_egress():
    tenants = [{
        "account_active": True,
        "buckets": [{"size_gb": 100, "egress_gb": 100}],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result["total_billed"] == 2.5


def test_excess_egress():
    tenants = [{
        "account_active": True,
        "buckets": [{"size_gb": 100, "egress_gb": 150}],
    }]
    result = process_storage_tenants(tenants, 10)
    # Storage: 2.50; excess egress: 50 * 0.08 = 4.00
    assert result["total_billed"] == 6.5


def test_backup_vault_fee():
    tenants = [{
        "account_active": True,
        "has_backup_vault": True,
        "buckets": [{"size_gb": 100}],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result["total_billed"] == 12.5


def test_four_flagged_buckets():
    tenants = [{
        "account_active": True,
        "buckets": [
            {"size_gb": 0},
            {"size_gb": 0},
            {"size_gb": 0},
            {"size_gb": 0},
        ],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result["status"] == "ZERO_USAGE"

def test_five_flagged_buckets():
    tenants = [{
        "account_active": True,
        "buckets": [
            {"size_gb": 0},
            {"size_gb": 0},
            {"size_gb": 0},
            {"size_gb": 0},
            {"size_gb": 0},
        ],
    }]
    result = process_storage_tenants(tenants, 10)
    assert result["status"] == "AUDIT_FLAGGED"

def test_no_replication_data():
    assert monitor_replication_latency([]) == "NO_DATA"


def test_normal_replication():
    assert monitor_replication_latency([[100, 150, 200]]) == "SYNCED"


def test_single_high_latency():
    assert monitor_replication_latency([[250]]) == "SYNCED"


def test_consecutive_high_latency():
    assert monitor_replication_latency([[250, 300]]) == "SYNC_LAG_ALERT"


def test_latency_streak_resets():
    assert monitor_replication_latency([[250, 100, 300]]) == "SYNCED"


def test_streak_does_not_carry_between_nodes():
    assert monitor_replication_latency([[250], [300]]) == "SYNCED"