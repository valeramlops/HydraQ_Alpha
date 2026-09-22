FROM golang:1.24-alpine AS build

ARG MINIO_RELEASE=RELEASE.2025-10-15T17-29-55Z

RUN apk add --no-cache git ca-certificates curl

WORKDIR /src

RUN git clone --depth 1 --branch ${MINIO_RELEASE} https://github.com/minio/minio.git . && \
    CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /usr/local/bin/minio .

RUN git clone --depth 1 https://github.com/minio/mc.git /mc && \
    cd /mc && \
    CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /usr/local/bin/mc .

FROM alpine:3.20

RUN apk add --no-cache ca-certificates curl

COPY --from=build /usr/local/bin/minio /usr/bin/minio
COPY --from=build /usr/local/bin/mc /usr/bin/mc

RUN adduser -D -u 1000 minio && \
    mkdir -p /data && \
    chown minio:minio /data

USER minio

EXPOSE 9000 9001

ENTRYPOINT ["minio"]
