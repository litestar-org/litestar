Nginx 反向代理
================

推荐使用 Nginx 作为 Litestar 项目的前端反向代理。

基本配置：

.. code-block:: nginx

    server {
        listen 80;
        server_name example.com;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

此配置可将所有流量转发至本地运行的 Litestar 服务。

更多安全与性能优化建议请参考 Nginx 官方文档。
