NODE_VERSION := $(shell tr -d '\n' < .nvmrc)
NODE_BIN := $(HOME)/.nvm/versions/node/v$(NODE_VERSION)/bin
UPDATE_MESSAGE ?= Frontend OTA update

.PHONY: deploy-front

deploy-front:
	cd client && PATH="$(NODE_BIN):$$PATH" npm run verify
	cd client && PATH="$(NODE_BIN):$$PATH" CI=1 npx eas-cli@latest update --platform ios --branch preview --environment preview --message "$(UPDATE_MESSAGE)"
