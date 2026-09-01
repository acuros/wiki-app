NODE_VERSION := $(shell tr -d '\n' < .nvmrc)
NODE_BIN := $(HOME)/.nvm/versions/node/v$(NODE_VERSION)/bin
UPDATE_MESSAGE ?= Frontend OTA update

.PHONY: deploy-front deploy-server

deploy-front:
	cd client && PATH="$(NODE_BIN):$$PATH" npm run verify
	cd client && PATH="$(NODE_BIN):$$PATH" CI=1 npx eas-cli@latest update --platform ios --branch preview --environment preview --message "$(UPDATE_MESSAGE)"

deploy-server:
	systemctl --user restart llm-wiki-web.service
	for attempt in $$(seq 1 10); do curl --fail --silent --show-error http://127.0.0.1:8787/health/ready && exit 0; sleep 1; done; exit 1
