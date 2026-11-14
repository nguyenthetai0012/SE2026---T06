from datetime import datetime, timezone
def soft_delete_device(device, user_role, user_building):
    if user_role != "Admin":
        raise PermissionError("Chỉ Admin mới có quyền xóa.")
    if user_building != device["building_id"]:
        raise PermissionError("Không có quyền trên tòa nhà này.") # Chống lộ dữ liệu
    if device["deleted_at"] is not None:
        raise ValueError("Thiết bị đã bị xóa.")
    device["deleted_at"] = datetime.now(timezone.utc).isoformat()
    return device