from src.backend.services.device_service import soft_delete_device
def test_soft_delete_device_success():
    # Giả lập dữ liệu
    device = {"id": "D1", "building_id": "B1", "deleted_at": None}
    # Hành động: Gọi hàm xóa mềm (hàm này chưa tồn tại)
    result = soft_delete_device(device, user_role="Admin", user_building="B1")
    # Kiểm chứng
    assert result["deleted_at"] is not None