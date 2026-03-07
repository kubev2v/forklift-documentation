FROM node:20-alpine
RUN apk add --no-cache ruby ruby-dev build-base python3 \
    && gem install asciidoctor --no-document
WORKDIR /docs
