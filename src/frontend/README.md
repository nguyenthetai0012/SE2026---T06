# Frontend APP-05

Ứng dụng web React + TypeScript + Vite theo lựa chọn trong baseline [PR #27](https://github.com/nguyenthetai0012/SE2026---T06/pull/27). PR #27 đang mở và baseline còn `PROPOSED`; scaffold này dùng lựa chọn stack theo yêu cầu Issue #11 để phát triển riêng, không đánh dấu các DTO/API là contract đã duyệt.

## Yêu cầu môi trường

- Node.js `22.12.0` (hoặc Node 22 từ `22.12` trở lên).
- npm `10.9.0` khi dùng Node `22.12.0`.

Phiên bản Node được ghim trong `.nvmrc`; `package.json` giới hạn Node 22. Lệnh kiểm chứng trong môi trường này:

```sh
npx --yes --package=node@22.12.0 --package=npm@10.9.0 -c 'node --version && npm --version'
```

## Cài đặt và chạy

```sh
npm ci
npm run dev -- --host 127.0.0.1
```

Chế độ mặc định là mock. Khi Backend triển khai API theo contract được nhóm duyệt, đặt `VITE_DATA_MODE=api` và `VITE_API_BASE_URL`; chỉ `src/api/repository.ts` chọn repository, còn endpoint/wire DTO và mapping được cô lập trong `src/api/`.

Trong Vite development, có thể thêm `?demo=empty`, `?demo=error-once`, `?demo=error-refresh`, `?demo=delayed`, `?demo=zero` hoặc `?demo=null-energy` vào URL để xem các trạng thái mock. Các lựa chọn này chỉ tạo response cục bộ, không gửi dữ liệu giả tới Backend.

## Kiểm tra

```sh
npm run lint
npm run typecheck
npm run test:run
npm run build
```

`dist/` và `node_modules/` là đầu ra cục bộ, không commit. Không dùng dữ liệu mock để suy ra công thức năng lượng, ngưỡng cảnh báo hoặc chính sách online/offline.
