部署策略
================

本主题介绍 Litestar 项目的常见部署方式，包括容器化、云服务、反向代理等。

- **容器化**：推荐使用 Docker 部署，便于环境隔离与扩展。
- **云服务**：可部署至 AWS、Azure、GCP 等主流云平台。
- **反向代理**：建议使用 Nginx 或 Traefik 作为前端代理，提升安全性与性能。

.. toctree::
    :titlesonly:
    :caption: 部署相关

    docker
    nginx
