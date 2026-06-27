.PHONY: act-lint act-test act-security act-build act-all

act-lint:
	act -j lint

act-test:
	act -j test

act-security:
	act -j security

act-build:
	act -j build

act-all:
	act -j lint && \
	act -j test && \
	act -j security && \
	act -j build
