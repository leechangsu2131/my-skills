"use strict";
var __classPrivateFieldSet = (this && this.__classPrivateFieldSet) || function (receiver, state, value, kind, f) {
    if (kind === "m") throw new TypeError("Private method is not writable");
    if (kind === "a" && !f) throw new TypeError("Private accessor was defined without a setter");
    if (typeof state === "function" ? receiver !== state || !f : !state.has(receiver)) throw new TypeError("Cannot write private member to an object whose class did not declare it");
    return (kind === "a" ? f.call(receiver, value) : f ? f.value = value : state.set(receiver, value)), value;
};
var __classPrivateFieldGet = (this && this.__classPrivateFieldGet) || function (receiver, state, kind, f) {
    if (kind === "a" && !f) throw new TypeError("Private accessor was defined without a getter");
    if (typeof state === "function" ? receiver !== state || !f : !state.has(receiver)) throw new TypeError("Cannot read private member from an object whose class did not declare it");
    return kind === "m" ? f : kind === "a" ? f.call(receiver) : f ? f.value : state.get(receiver);
};
var _Client_auth, _Client_logLevel, _Client_logger, _Client_prefixUrl, _Client_timeoutMs, _Client_notionVersion, _Client_fetch, _Client_agent, _Client_userAgent, _Client_maxRetries, _Client_initialRetryDelayMs, _Client_maxRetryDelayMs;
Object.defineProperty(exports, "__esModule", { value: true });
const logging_1 = require("./logging");
const errors_1 = require("./errors");
const utils_1 = require("./utils");
const api_endpoints_1 = require("./api-endpoints");
const package_json_1 = require("../package.json");
class Client {
    constructor(options) {
        var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m;
        _Client_auth.set(this, void 0);
        _Client_logLevel.set(this, void 0);
        _Client_logger.set(this, void 0);
        _Client_prefixUrl.set(this, void 0);
        _Client_timeoutMs.set(this, void 0);
        _Client_notionVersion.set(this, void 0);
        _Client_fetch.set(this, void 0);
        _Client_agent.set(this, void 0);
        _Client_userAgent.set(this, void 0);
        _Client_maxRetries.set(this, void 0);
        _Client_initialRetryDelayMs.set(this, void 0);
        _Client_maxRetryDelayMs.set(this, void 0);
        /*
         * Notion API endpoints
         */
        this.blocks = {
            /**
             * Retrieve block
             */
            retrieve: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.getBlock);
                return this.request({
                    path: api_endpoints_1.getBlock.path(args),
                    method: api_endpoints_1.getBlock.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.getBlock.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.getBlock.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Update block
             */
            update: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.updateBlock);
                return this.request({
                    path: api_endpoints_1.updateBlock.path(args),
                    method: api_endpoints_1.updateBlock.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.updateBlock.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.updateBlock.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Delete block
             */
            delete: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.deleteBlock);
                return this.request({
                    path: api_endpoints_1.deleteBlock.path(args),
                    method: api_endpoints_1.deleteBlock.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.deleteBlock.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.deleteBlock.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            children: {
                /**
                 * Append block children
                 */
                append: (args) => {
                    this.warnUnknownParams(args, api_endpoints_1.appendBlockChildren);
                    return this.request({
                        path: api_endpoints_1.appendBlockChildren.path(args),
                        method: api_endpoints_1.appendBlockChildren.method,
                        query: (0, utils_1.pick)(args, api_endpoints_1.appendBlockChildren.queryParams),
                        body: (0, utils_1.pick)(args, api_endpoints_1.appendBlockChildren.bodyParams),
                        auth: args === null || args === void 0 ? void 0 : args.auth,
                    });
                },
                /**
                 * Retrieve block children
                 */
                list: (args) => {
                    this.warnUnknownParams(args, api_endpoints_1.listBlockChildren);
                    return this.request({
                        path: api_endpoints_1.listBlockChildren.path(args),
                        method: api_endpoints_1.listBlockChildren.method,
                        query: (0, utils_1.pick)(args, api_endpoints_1.listBlockChildren.queryParams),
                        body: (0, utils_1.pick)(args, api_endpoints_1.listBlockChildren.bodyParams),
                        auth: args === null || args === void 0 ? void 0 : args.auth,
                    });
                },
            },
        };
        this.databases = {
            /**
             * Retrieve a database
             */
            retrieve: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.getDatabase);
                return this.request({
                    path: api_endpoints_1.getDatabase.path(args),
                    method: api_endpoints_1.getDatabase.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.getDatabase.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.getDatabase.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Create a database
             */
            create: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.createDatabase);
                return this.request({
                    path: api_endpoints_1.createDatabase.path(),
                    method: api_endpoints_1.createDatabase.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.createDatabase.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.createDatabase.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Update a database
             */
            update: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.updateDatabase);
                return this.request({
                    path: api_endpoints_1.updateDatabase.path(args),
                    method: api_endpoints_1.updateDatabase.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.updateDatabase.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.updateDatabase.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
        };
        this.dataSources = {
            /**
             * Retrieve a data source
             */
            retrieve: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.getDataSource);
                return this.request({
                    path: api_endpoints_1.getDataSource.path(args),
                    method: api_endpoints_1.getDataSource.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.getDataSource.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.getDataSource.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Query a data source
             */
            query: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.queryDataSource);
                return this.request({
                    path: api_endpoints_1.queryDataSource.path(args),
                    method: api_endpoints_1.queryDataSource.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.queryDataSource.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.queryDataSource.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Create a data source
             */
            create: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.createDataSource);
                return this.request({
                    path: api_endpoints_1.createDataSource.path(),
                    method: api_endpoints_1.createDataSource.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.createDataSource.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.createDataSource.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Update a data source
             */
            update: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.updateDataSource);
                return this.request({
                    path: api_endpoints_1.updateDataSource.path(args),
                    method: api_endpoints_1.updateDataSource.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.updateDataSource.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.updateDataSource.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * List page templates that are available for a data source
             */
            listTemplates: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.listDataSourceTemplates);
                return this.request({
                    path: api_endpoints_1.listDataSourceTemplates.path(args),
                    method: api_endpoints_1.listDataSourceTemplates.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.listDataSourceTemplates.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.listDataSourceTemplates.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
        };
        this.pages = {
            /**
             * Create a page
             */
            create: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.createPage);
                return this.request({
                    path: api_endpoints_1.createPage.path(),
                    method: api_endpoints_1.createPage.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.createPage.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.createPage.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Retrieve a page
             */
            retrieve: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.getPage);
                return this.request({
                    path: api_endpoints_1.getPage.path(args),
                    method: api_endpoints_1.getPage.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.getPage.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.getPage.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Update page properties
             */
            update: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.updatePage);
                return this.request({
                    path: api_endpoints_1.updatePage.path(args),
                    method: api_endpoints_1.updatePage.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.updatePage.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.updatePage.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Move a page
             */
            move: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.movePage);
                return this.request({
                    path: api_endpoints_1.movePage.path(args),
                    method: api_endpoints_1.movePage.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.movePage.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.movePage.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Retrieve a page as markdown
             */
            retrieveMarkdown: (args) => {
                return this.request({
                    path: api_endpoints_1.getPageMarkdown.path(args),
                    method: api_endpoints_1.getPageMarkdown.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.getPageMarkdown.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.getPageMarkdown.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Update a page's content as markdown
             */
            updateMarkdown: (args) => {
                return this.request({
                    path: api_endpoints_1.updatePageMarkdown.path(args),
                    method: api_endpoints_1.updatePageMarkdown.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.updatePageMarkdown.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.updatePageMarkdown.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            properties: {
                /**
                 * Retrieve page property
                 */
                retrieve: (args) => {
                    this.warnUnknownParams(args, api_endpoints_1.getPageProperty);
                    return this.request({
                        path: api_endpoints_1.getPageProperty.path(args),
                        method: api_endpoints_1.getPageProperty.method,
                        query: (0, utils_1.pick)(args, api_endpoints_1.getPageProperty.queryParams),
                        body: (0, utils_1.pick)(args, api_endpoints_1.getPageProperty.bodyParams),
                        auth: args === null || args === void 0 ? void 0 : args.auth,
                    });
                },
            },
        };
        this.users = {
            /**
             * Retrieve a user
             */
            retrieve: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.getUser);
                return this.request({
                    path: api_endpoints_1.getUser.path(args),
                    method: api_endpoints_1.getUser.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.getUser.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.getUser.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * List all users
             */
            list: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.listUsers);
                return this.request({
                    path: api_endpoints_1.listUsers.path(),
                    method: api_endpoints_1.listUsers.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.listUsers.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.listUsers.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Get details about bot
             */
            me: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.getSelf);
                return this.request({
                    path: api_endpoints_1.getSelf.path(),
                    method: api_endpoints_1.getSelf.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.getSelf.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.getSelf.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
        };
        this.comments = {
            /**
             * Create a comment
             */
            create: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.createComment);
                return this.request({
                    path: api_endpoints_1.createComment.path(),
                    method: api_endpoints_1.createComment.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.createComment.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.createComment.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * List comments
             */
            list: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.listComments);
                return this.request({
                    path: api_endpoints_1.listComments.path(),
                    method: api_endpoints_1.listComments.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.listComments.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.listComments.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Retrieve a comment
             */
            retrieve: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.getComment);
                return this.request({
                    path: api_endpoints_1.getComment.path(args),
                    method: api_endpoints_1.getComment.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.getComment.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.getComment.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
        };
        this.fileUploads = {
            /**
             * Create a file upload
             */
            create: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.createFileUpload);
                return this.request({
                    path: api_endpoints_1.createFileUpload.path(),
                    method: api_endpoints_1.createFileUpload.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.createFileUpload.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.createFileUpload.bodyParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Retrieve a file upload
             */
            retrieve: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.getFileUpload);
                return this.request({
                    path: api_endpoints_1.getFileUpload.path(args),
                    method: api_endpoints_1.getFileUpload.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.getFileUpload.queryParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * List file uploads
             */
            list: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.listFileUploads);
                return this.request({
                    path: api_endpoints_1.listFileUploads.path(),
                    method: api_endpoints_1.listFileUploads.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.listFileUploads.queryParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Send a file upload
             *
             * Requires a `file_upload_id`, obtained from the `id` of the Create File
             * Upload API response.
             *
             * The `file` parameter contains the raw file contents or Blob/File object
             * under `file.data`, and an optional `file.filename` string.
             *
             * Supply a stringified `part_number` parameter when using file uploads
             * in multi-part mode.
             *
             * This endpoint sends HTTP multipart/form-data instead of JSON parameters.
             */
            send: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.sendFileUpload);
                return this.request({
                    path: api_endpoints_1.sendFileUpload.path(args),
                    method: api_endpoints_1.sendFileUpload.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.sendFileUpload.queryParams),
                    formDataParams: (0, utils_1.pick)(args, api_endpoints_1.sendFileUpload.formDataParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
            /**
             * Complete a file upload
             */
            complete: (args) => {
                this.warnUnknownParams(args, api_endpoints_1.completeFileUpload);
                return this.request({
                    path: api_endpoints_1.completeFileUpload.path(args),
                    method: api_endpoints_1.completeFileUpload.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.completeFileUpload.queryParams),
                    auth: args === null || args === void 0 ? void 0 : args.auth,
                });
            },
        };
        /**
         * Search
         */
        this.search = (args) => {
            this.warnUnknownParams(args, api_endpoints_1.search);
            return this.request({
                path: api_endpoints_1.search.path(),
                method: api_endpoints_1.search.method,
                query: (0, utils_1.pick)(args, api_endpoints_1.search.queryParams),
                body: (0, utils_1.pick)(args, api_endpoints_1.search.bodyParams),
                auth: args === null || args === void 0 ? void 0 : args.auth,
            });
        };
        this.oauth = {
            /**
             * Get token
             */
            token: (args) => {
                return this.request({
                    path: api_endpoints_1.oauthToken.path(),
                    method: api_endpoints_1.oauthToken.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.oauthToken.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.oauthToken.bodyParams),
                    auth: {
                        client_id: args.client_id,
                        client_secret: args.client_secret,
                    },
                });
            },
            /**
             * Introspect token
             */
            introspect: (args) => {
                return this.request({
                    path: api_endpoints_1.oauthIntrospect.path(),
                    method: api_endpoints_1.oauthIntrospect.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.oauthIntrospect.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.oauthIntrospect.bodyParams),
                    auth: {
                        client_id: args.client_id,
                        client_secret: args.client_secret,
                    },
                });
            },
            /**
             * Revoke token
             */
            revoke: (args) => {
                return this.request({
                    path: api_endpoints_1.oauthRevoke.path(),
                    method: api_endpoints_1.oauthRevoke.method,
                    query: (0, utils_1.pick)(args, api_endpoints_1.oauthRevoke.queryParams),
                    body: (0, utils_1.pick)(args, api_endpoints_1.oauthRevoke.bodyParams),
                    auth: {
                        client_id: args.client_id,
                        client_secret: args.client_secret,
                    },
                });
            },
        };
        __classPrivateFieldSet(this, _Client_auth, options === null || options === void 0 ? void 0 : options.auth, "f");
        __classPrivateFieldSet(this, _Client_logLevel, (_a = options === null || options === void 0 ? void 0 : options.logLevel) !== null && _a !== void 0 ? _a : logging_1.LogLevel.WARN, "f");
        __classPrivateFieldSet(this, _Client_logger, (_b = options === null || options === void 0 ? void 0 : options.logger) !== null && _b !== void 0 ? _b : (0, logging_1.makeConsoleLogger)(package_json_1.name), "f");
        __classPrivateFieldSet(this, _Client_prefixUrl, `${(_c = options === null || options === void 0 ? void 0 : options.baseUrl) !== null && _c !== void 0 ? _c : "https://api.notion.com"}/v1/`, "f");
        __classPrivateFieldSet(this, _Client_timeoutMs, (_d = options === null || options === void 0 ? void 0 : options.timeoutMs) !== null && _d !== void 0 ? _d : 60000, "f");
        __classPrivateFieldSet(this, _Client_notionVersion, (_e = options === null || options === void 0 ? void 0 : options.notionVersion) !== null && _e !== void 0 ? _e : Client.defaultNotionVersion, "f");
        __classPrivateFieldSet(this, _Client_fetch, (_f = options === null || options === void 0 ? void 0 : options.fetch) !== null && _f !== void 0 ? _f : fetch.bind(globalThis), "f");
        __classPrivateFieldSet(this, _Client_agent, options === null || options === void 0 ? void 0 : options.agent, "f");
        __classPrivateFieldSet(this, _Client_userAgent, `notionhq-client/${package_json_1.version}`, "f");
        if ((options === null || options === void 0 ? void 0 : options.retry) === false) {
            __classPrivateFieldSet(this, _Client_maxRetries, 0, "f");
            __classPrivateFieldSet(this, _Client_initialRetryDelayMs, 0, "f");
            __classPrivateFieldSet(this, _Client_maxRetryDelayMs, 0, "f");
        }
        else {
            __classPrivateFieldSet(this, _Client_maxRetries, (_h = (_g = options === null || options === void 0 ? void 0 : options.retry) === null || _g === void 0 ? void 0 : _g.maxRetries) !== null && _h !== void 0 ? _h : 2, "f");
            __classPrivateFieldSet(this, _Client_initialRetryDelayMs, (_k = (_j = options === null || options === void 0 ? void 0 : options.retry) === null || _j === void 0 ? void 0 : _j.initialRetryDelayMs) !== null && _k !== void 0 ? _k : 1000, "f");
            __classPrivateFieldSet(this, _Client_maxRetryDelayMs, (_m = (_l = options === null || options === void 0 ? void 0 : options.retry) === null || _l === void 0 ? void 0 : _l.maxRetryDelayMs) !== null && _m !== void 0 ? _m : 60000, "f");
        }
    }
    /**
     * Sends a request.
     */
    async request(args) {
        const { path, method, query, body, formDataParams, auth } = args;
        (0, errors_1.validateRequestPath)(path);
        this.log(logging_1.LogLevel.INFO, "request start", { method, path });
        const url = this.buildRequestUrl(path, query);
        const bodyAsJsonString = this.serializeBody(body);
        const headers = this.buildRequestHeaders(args.headers, auth, bodyAsJsonString);
        const formData = this.buildFormData(formDataParams, headers);
        return this.executeWithRetry({
            url,
            method,
            path,
            headers,
            body: bodyAsJsonString !== null && bodyAsJsonString !== void 0 ? bodyAsJsonString : formData,
        });
    }
    /**
     * Builds the full URL with query parameters.
     */
    buildRequestUrl(path, query) {
        const url = new URL(`${__classPrivateFieldGet(this, _Client_prefixUrl, "f")}${path}`);
        if (query) {
            for (const [key, value] of Object.entries(query)) {
                if (value !== undefined) {
                    if (Array.isArray(value)) {
                        for (const val of value) {
                            url.searchParams.append(key, decodeURIComponent(val));
                        }
                    }
                    else {
                        url.searchParams.append(key, String(value));
                    }
                }
            }
        }
        return url;
    }
    /**
     * Serializes the request body to JSON string if non-empty.
     */
    serializeBody(body) {
        if (!body || Object.entries(body).length === 0) {
            return undefined;
        }
        return JSON.stringify(body);
    }
    /**
     * Builds the request headers including auth and content-type.
     */
    buildRequestHeaders(customHeaders, auth, bodyAsJsonString) {
        const authorizationHeader = this.buildAuthHeader(auth);
        const headers = {
            ...customHeaders,
            ...authorizationHeader,
            "Notion-Version": __classPrivateFieldGet(this, _Client_notionVersion, "f"),
            "user-agent": __classPrivateFieldGet(this, _Client_userAgent, "f"),
        };
        if (bodyAsJsonString !== undefined) {
            headers["content-type"] = "application/json";
        }
        return headers;
    }
    /**
     * Builds the authorization header based on auth type.
     */
    buildAuthHeader(auth) {
        if (typeof auth === "object") {
            const unencodedCredential = `${auth.client_id}:${auth.client_secret}`;
            const encodedCredential = Buffer.from(unencodedCredential).toString("base64");
            return { authorization: `Basic ${encodedCredential}` };
        }
        return this.authAsHeaders(auth);
    }
    /**
     * Builds FormData from form parameters if provided.
     * Also removes content-type header to let fetch set the boundary.
     */
    buildFormData(formDataParams, headers) {
        if (!formDataParams) {
            return undefined;
        }
        delete headers["content-type"];
        const formData = new FormData();
        for (const [key, value] of Object.entries(formDataParams)) {
            if (typeof value === "string") {
                formData.append(key, value);
            }
            else if (typeof value === "object") {
                formData.append(key, typeof value.data === "object" ? value.data : new Blob([value.data]), value.filename);
            }
        }
        return formData;
    }
    /**
     * Executes the request with retry logic.
     */
    async executeWithRetry(args) {
        const { url, method, path, headers, body } = args;
        let attempt = 0;
        // eslint-disable-next-line no-constant-condition
        while (true) {
            try {
                return await this.executeSingleRequest({
                    url,
                    method,
                    path,
                    headers,
                    body,
                });
            }
            catch (error) {
                if (!(0, errors_1.isNotionClientError)(error)) {
                    throw error;
                }
                this.logRequestError(error, attempt);
                if (attempt < __classPrivateFieldGet(this, _Client_maxRetries, "f") && this.canRetry(error, method)) {
                    const delayMs = this.calculateRetryDelay(error, attempt);
                    this.log(logging_1.LogLevel.INFO, "retrying request", {
                        method,
                        path,
                        attempt: attempt + 1,
                        delayMs,
                    });
                    await this.sleep(delayMs);
                    attempt++;
                    continue;
                }
                throw error;
            }
        }
    }
    /**
     * Executes a single HTTP request (no retry).
     */
    async executeSingleRequest(args) {
        const { url, method, path, headers, body } = args;
        const response = await errors_1.RequestTimeoutError.rejectAfterTimeout(__classPrivateFieldGet(this, _Client_fetch, "f").call(this, url.toString(), {
            method: method.toUpperCase(),
            headers,
            body,
            agent: __classPrivateFieldGet(this, _Client_agent, "f"),
        }), __classPrivateFieldGet(this, _Client_timeoutMs, "f"));
        const responseText = await response.text();
        if (!response.ok) {
            throw (0, errors_1.buildRequestError)(response, responseText);
        }
        const responseJson = JSON.parse(responseText);
        this.log(logging_1.LogLevel.INFO, "request success", {
            method,
            path,
            ...this.extractRequestId(responseJson),
        });
        return responseJson;
    }
    /**
     * Logs a request error with appropriate detail level.
     */
    logRequestError(error, attempt) {
        this.log(logging_1.LogLevel.WARN, "request fail", {
            code: error.code,
            message: error.message,
            attempt,
            ...this.extractRequestId(error),
        });
        if ((0, errors_1.isHTTPResponseError)(error)) {
            this.log(logging_1.LogLevel.DEBUG, "failed response body", {
                body: error.body,
            });
        }
    }
    /**
     * Extracts request_id from an object if present.
     */
    extractRequestId(obj) {
        if (obj &&
            typeof obj === "object" &&
            "request_id" in obj &&
            typeof obj.request_id === "string") {
            return { requestId: obj.request_id };
        }
        return {};
    }
    /**
     * Determines if an error can be retried based on its error code and method.
     * Rate limits (429) are always retryable since the server explicitly asks us
     * to retry. Server errors (500, 503) are only retried for idempotent methods
     * (GET, DELETE) to avoid duplicate side effects.
     */
    canRetry(error, method) {
        if (!errors_1.APIResponseError.isAPIResponseError(error)) {
            return false;
        }
        // Rate limits are always retryable - server says "try again later"
        if (error.code === errors_1.APIErrorCode.RateLimited) {
            return true;
        }
        // Server errors only retry for idempotent methods
        const isIdempotent = method === "get" || method === "delete";
        if (isIdempotent) {
            return (error.code === errors_1.APIErrorCode.InternalServerError ||
                error.code === errors_1.APIErrorCode.ServiceUnavailable);
        }
        return false;
    }
    /**
     * Calculates the delay before the next retry attempt.
     * Uses retry-after header if present, otherwise exponential back-off with
     * jitter.
     */
    calculateRetryDelay(error, attempt) {
        // Try to get retry-after from the error headers
        if (errors_1.APIResponseError.isAPIResponseError(error)) {
            const retryAfterMs = this.parseRetryAfterHeader(error.headers);
            if (retryAfterMs !== undefined) {
                return Math.min(retryAfterMs, __classPrivateFieldGet(this, _Client_maxRetryDelayMs, "f"));
            }
        }
        // Exponential back-off with full jitter
        const baseDelay = __classPrivateFieldGet(this, _Client_initialRetryDelayMs, "f") * Math.pow(2, attempt);
        const jitter = Math.random();
        return Math.min(baseDelay * jitter + baseDelay / 2, __classPrivateFieldGet(this, _Client_maxRetryDelayMs, "f"));
    }
    /**
     * Parses the retry-after header value.
     * Supports both delta-seconds (e.g., "120") and HTTP-date formats.
     * Returns the delay in milliseconds, or undefined if not present or invalid.
     */
    parseRetryAfterHeader(headers) {
        var _a, _b;
        if (!headers) {
            return undefined;
        }
        let retryAfterValue = null;
        // Handle Headers object (standard fetch API)
        if (typeof headers === "object" && "get" in headers) {
            const headersObj = headers;
            retryAfterValue = headersObj.get("retry-after");
        }
        // Handle plain object
        else if (typeof headers === "object") {
            const headersRecord = headers;
            retryAfterValue =
                (_b = (_a = headersRecord["retry-after"]) !== null && _a !== void 0 ? _a : headersRecord["Retry-After"]) !== null && _b !== void 0 ? _b : null;
        }
        if (!retryAfterValue) {
            return undefined;
        }
        // Try parsing as delta-seconds (integer)
        const seconds = parseInt(retryAfterValue, 10);
        if (!isNaN(seconds) && seconds >= 0) {
            return seconds * 1000;
        }
        // Try parsing as HTTP-date
        const date = Date.parse(retryAfterValue);
        if (!isNaN(date)) {
            const delayMs = date - Date.now();
            return delayMs > 0 ? delayMs : 0;
        }
        return undefined;
    }
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    /**
     * Logs a warning when the caller passes parameters that are not recognized
     * by the endpoint definition. This helps catch typos and renamed parameters
     * (e.g. `archived` vs `in_trash` for `databases.update`) that would
     * otherwise be silently dropped by `pick()`.
     */
    warnUnknownParams(args, endpoint) {
        var _a;
        if (!args || typeof args !== "object")
            return;
        const unknownKeys = (0, utils_1.getUnknownParams)(args, endpoint);
        if (unknownKeys.length > 0) {
            this.log(logging_1.LogLevel.WARN, "unknown parameters were ignored", {
                unknownParams: unknownKeys,
                knownParams: [
                    ...endpoint.pathParams,
                    ...endpoint.queryParams,
                    ...endpoint.bodyParams,
                    ...((_a = endpoint.formDataParams) !== null && _a !== void 0 ? _a : []),
                ],
            });
        }
    }
    /**
     * Emits a log message to the console.
     *
     * @param level The level for this message
     * @param args Arguments to send to the console
     */
    log(level, message, extraInfo) {
        if ((0, logging_1.logLevelSeverity)(level) >= (0, logging_1.logLevelSeverity)(__classPrivateFieldGet(this, _Client_logLevel, "f"))) {
            __classPrivateFieldGet(this, _Client_logger, "f").call(this, level, message, extraInfo);
        }
    }
    /**
     * Transforms an API key or access token into a headers object suitable for an HTTP request.
     *
     * This method uses the instance's value as the default when the input is undefined. If neither are defined, it returns
     * an empty object
     *
     * @param auth API key or access token
     * @returns headers key-value object
     */
    authAsHeaders(auth) {
        const headers = {};
        const authHeaderValue = auth !== null && auth !== void 0 ? auth : __classPrivateFieldGet(this, _Client_auth, "f");
        if (authHeaderValue !== undefined) {
            headers["authorization"] = `Bearer ${authHeaderValue}`;
        }
        return headers;
    }
}
_Client_auth = new WeakMap(), _Client_logLevel = new WeakMap(), _Client_logger = new WeakMap(), _Client_prefixUrl = new WeakMap(), _Client_timeoutMs = new WeakMap(), _Client_notionVersion = new WeakMap(), _Client_fetch = new WeakMap(), _Client_agent = new WeakMap(), _Client_userAgent = new WeakMap(), _Client_maxRetries = new WeakMap(), _Client_initialRetryDelayMs = new WeakMap(), _Client_maxRetryDelayMs = new WeakMap();
Client.defaultNotionVersion = "2025-09-03";
exports.default = Client;
//# sourceMappingURL=Client.js.map