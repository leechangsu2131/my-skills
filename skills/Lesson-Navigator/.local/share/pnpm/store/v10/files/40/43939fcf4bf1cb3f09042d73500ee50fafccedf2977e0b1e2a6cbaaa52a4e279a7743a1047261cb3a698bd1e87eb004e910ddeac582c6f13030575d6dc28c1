import { camel, generateFormDataAndUrlEncodedFunction, generateMutatorConfig, generateMutatorRequestOptions, generateOptions, generateVerbImports, getAngularFilteredParamsCallExpression, getAngularFilteredParamsHelperBody, getDefaultContentType, isBoolean, pascal, sanitize, toObjectString } from "@orval/core";

//#region src/index.ts
const ANGULAR_DEPENDENCIES = [
	{
		exports: [
			{
				name: "HttpClient",
				values: true
			},
			{
				name: "HttpHeaders",
				values: true
			},
			{ name: "HttpParams" },
			{ name: "HttpContext" },
			{
				name: "HttpResponse",
				alias: "AngularHttpResponse"
			},
			{ name: "HttpEvent" }
		],
		dependency: "@angular/common/http"
	},
	{
		exports: [{
			name: "Injectable",
			values: true
		}, {
			name: "inject",
			values: true
		}],
		dependency: "@angular/core"
	},
	{
		exports: [{
			name: "Observable",
			values: true
		}],
		dependency: "rxjs"
	}
];
const PRIMITIVE_RESPONSE_TYPES = [
	"string",
	"number",
	"boolean",
	"void",
	"unknown"
];
const isPrimitiveResponseType = (typeName) => typeName != void 0 && PRIMITIVE_RESPONSE_TYPES.includes(typeName);
const hasSchemaImport = (imports, typeName) => typeName != void 0 && imports.some((imp) => imp.name === typeName);
const getSchemaValueRef = (typeName) => typeName === "Error" ? "ErrorSchema" : typeName;
const getAngularDependencies = () => [...ANGULAR_DEPENDENCIES];
const generateAngularTitle = (title) => {
	return `${pascal(sanitize(title))}Service`;
};
const createAngularHeader = () => ({ title, isRequestOptions, isMutator, isGlobalMutator, provideIn, verbOptions, tag }) => {
	const stringTag = tag;
	const hasQueryParams = (stringTag ? Object.values(verbOptions).filter((v) => v.tags.some((t) => camel(t) === camel(stringTag))) : Object.values(verbOptions)).some((v) => v.queryParams);
	return `
${isRequestOptions && !isGlobalMutator ? `interface HttpClientOptions {
  readonly headers?: HttpHeaders | Record<string, string | string[]>;
  readonly context?: HttpContext;
  readonly params?:
        | HttpParams
      | Record<string, string | number | boolean | Array<string | number | boolean>>;
  readonly reportProgress?: boolean;
  readonly withCredentials?: boolean;
  readonly credentials?: RequestCredentials;
  readonly keepalive?: boolean;
  readonly priority?: RequestPriority;
  readonly cache?: RequestCache;
  readonly mode?: RequestMode;
  readonly redirect?: RequestRedirect;
  readonly referrer?: string;
  readonly integrity?: string;
  readonly referrerPolicy?: ReferrerPolicy;
  readonly transferCache?: {includeHeaders?: string[]} | boolean;
}

${hasQueryParams ? getAngularFilteredParamsHelperBody() : ""}` : ""}

${isRequestOptions && isMutator ? `// eslint-disable-next-line
    type ThirdParameter<T extends (...args: any) => any> = T extends (
  config: any,
  httpClient: any,
  args: infer P,
) => any
  ? P
  : never;` : ""}

@Injectable(${provideIn ? `{ providedIn: '${isBoolean(provideIn) ? "root" : provideIn}' }` : ""})
export class ${title} {
  private readonly http = inject(HttpClient);
`;
};
const generateAngularHeader = (params) => createAngularHeader()(params);
const standaloneFooterReturnTypesToWrite = /* @__PURE__ */ new Map();
const createAngularFooter = (returnTypesToWrite) => ({ operationNames }) => {
	let footer = "}\n\n";
	for (const operationName of operationNames) if (returnTypesToWrite.has(operationName)) footer += returnTypesToWrite.get(operationName) + "\n";
	return footer;
};
const generateAngularFooter = (params) => createAngularFooter(standaloneFooterReturnTypesToWrite)(params);
const generateImplementation = (returnTypesToWrite, { headers, queryParams, operationName, response, mutator, body, props, verb, override, formData, formUrlEncoded, paramsSerializer }, { route, context }) => {
	const isRequestOptions = override.requestOptions !== false;
	const isFormData = !override.formData.disabled;
	const isFormUrlEncoded = override.formUrlEncoded !== false;
	const isExactOptionalPropertyTypes = !!context.output.tsconfig?.compilerOptions?.exactOptionalPropertyTypes;
	const bodyForm = generateFormDataAndUrlEncodedFunction({
		formData,
		formUrlEncoded,
		body,
		isFormData,
		isFormUrlEncoded
	});
	const dataType = response.definition.success || "unknown";
	const isPrimitiveType = isPrimitiveResponseType(dataType);
	const hasSchema = hasSchemaImport(response.imports, dataType);
	const isZodOutput = typeof context.output.schemas === "object" && context.output.schemas.type === "zod";
	const shouldValidateResponse = override.angular.runtimeValidation && isZodOutput && !isPrimitiveType && hasSchema;
	const schemaValueRef = shouldValidateResponse ? getSchemaValueRef(dataType) : dataType;
	const validationPipe = shouldValidateResponse ? `.pipe(map(data => ${schemaValueRef}.parse(data) as TData))` : "";
	returnTypesToWrite.set(operationName, `export type ${pascal(operationName)}ClientResult = NonNullable<${dataType}>`);
	if (mutator) {
		const mutatorConfig = generateMutatorConfig({
			route,
			body,
			headers,
			queryParams,
			response,
			verb,
			isFormData,
			isFormUrlEncoded,
			hasSignal: false,
			isExactOptionalPropertyTypes,
			isAngular: true
		});
		const requestOptions = isRequestOptions ? generateMutatorRequestOptions(override.requestOptions, mutator.hasThirdArg) : "";
		return ` ${operationName}<TData = ${dataType}>(\n    ${mutator.bodyTypeName && body.definition ? toObjectString(props, "implementation").replace(new RegExp(String.raw`(\w*):\s?${body.definition}`), `$1: ${mutator.bodyTypeName}<${body.definition}>`) : toObjectString(props, "implementation")}\n ${isRequestOptions && mutator.hasThirdArg ? `options?: ThirdParameter<typeof ${mutator.name}>` : ""}) {${bodyForm}
      return ${mutator.name}<TData>(
      ${mutatorConfig},
      this.http,
      ${requestOptions});
    }
  `;
	}
	const optionsBase = {
		route,
		body,
		headers,
		queryParams,
		response,
		verb,
		requestOptions: override.requestOptions,
		isFormData,
		isFormUrlEncoded,
		paramsSerializer,
		paramsSerializerOptions: override.paramsSerializerOptions,
		isAngular: true,
		isExactOptionalPropertyTypes,
		hasSignal: false
	};
	const propsDefinition = toObjectString(props, "definition");
	const successTypes = response.types.success;
	const uniqueContentTypes = [...new Set(successTypes.map((t) => t.contentType).filter(Boolean))];
	const hasMultipleContentTypes = uniqueContentTypes.length > 1;
	const needsObserveBranching = isRequestOptions && !hasMultipleContentTypes;
	const angularParamsRef = needsObserveBranching && queryParams ? "filteredParams" : void 0;
	let paramsDeclaration = "";
	if (angularParamsRef && queryParams) {
		const callExpr = getAngularFilteredParamsCallExpression("{...params, ...options?.params}", queryParams.requiredNullableKeys ?? []);
		paramsDeclaration = paramsSerializer ? `const ${angularParamsRef} = ${paramsSerializer.name}(${callExpr});\n\n    ` : `const ${angularParamsRef} = ${callExpr};\n\n    `;
	}
	const optionsInput = {
		...optionsBase,
		...angularParamsRef ? { angularParamsRef } : {}
	};
	const options = generateOptions(optionsInput);
	const defaultContentType = hasMultipleContentTypes ? uniqueContentTypes.includes("text/plain") ? "text/plain" : getDefaultContentType(uniqueContentTypes) : uniqueContentTypes[0] ?? "application/json";
	const getContentTypeReturnType = (contentType, value) => {
		if (!contentType) return value;
		if (contentType.includes("json") || contentType.includes("+json")) return value;
		if (contentType.startsWith("text/") || contentType.includes("xml")) return "string";
		return "Blob";
	};
	const jsonSuccessValues = [...new Set(successTypes.filter(({ contentType }) => !!contentType && (contentType.includes("json") || contentType.includes("+json"))).map(({ value }) => value))];
	const jsonReturnType = jsonSuccessValues.length > 0 ? jsonSuccessValues.join(" | ") : "unknown";
	let jsonValidationPipe = shouldValidateResponse ? `.pipe(map(data => ${schemaValueRef}.parse(data)))` : "";
	if (hasMultipleContentTypes && !shouldValidateResponse && override.angular.runtimeValidation && isZodOutput && jsonSuccessValues.length === 1) {
		const jsonType = jsonSuccessValues[0];
		const jsonIsPrimitive = isPrimitiveResponseType(jsonType);
		const jsonHasSchema = hasSchemaImport(response.imports, jsonType);
		if (!jsonIsPrimitive && jsonHasSchema) jsonValidationPipe = `.pipe(map(data => ${getSchemaValueRef(jsonType)}.parse(data)))`;
	}
	const multiImplementationReturnType = `Observable<${jsonReturnType} | string | Blob>`;
	const observeOptions = needsObserveBranching ? {
		body: generateOptions({
			...optionsInput,
			angularObserve: "body"
		}),
		events: generateOptions({
			...optionsInput,
			angularObserve: "events"
		}),
		response: generateOptions({
			...optionsInput,
			angularObserve: "response"
		})
	} : void 0;
	const isModelType = dataType !== "Blob" && dataType !== "string";
	let functionName = operationName;
	if (isModelType && !hasMultipleContentTypes) functionName += `<TData = ${dataType}>`;
	let contentTypeOverloads = "";
	if (hasMultipleContentTypes && isRequestOptions) {
		const requiredProps = props.filter((p) => p.required && !p.default);
		const optionalProps = props.filter((p) => !p.required || p.default);
		contentTypeOverloads = successTypes.filter((t) => t.contentType).map(({ contentType, value }) => {
			const returnType = getContentTypeReturnType(contentType, value);
			return `${operationName}(${[
				requiredProps.map((p) => p.definition).join(",\n    "),
				`accept: '${contentType}'`,
				optionalProps.map((p) => p.definition).join(",\n    ")
			].filter(Boolean).join(",\n    ")}, options?: HttpClientOptions): Observable<${returnType}>;`;
		}).join("\n  ");
		const allParams = [
			requiredProps.map((p) => p.definition).join(",\n    "),
			"accept?: string",
			optionalProps.map((p) => p.definition).join(",\n    ")
		].filter(Boolean).join(",\n    ");
		contentTypeOverloads += `\n  ${operationName}(${allParams}, options?: HttpClientOptions): ${multiImplementationReturnType};`;
	}
	const observeOverloads = isRequestOptions && !hasMultipleContentTypes ? `${functionName}(${propsDefinition} options?: HttpClientOptions & { observe?: 'body' }): Observable<${isModelType ? "TData" : dataType}>;
 ${functionName}(${propsDefinition} options?: HttpClientOptions & { observe: 'events' }): Observable<HttpEvent<${isModelType ? "TData" : dataType}>>;
 ${functionName}(${propsDefinition} options?: HttpClientOptions & { observe: 'response' }): Observable<AngularHttpResponse<${isModelType ? "TData" : dataType}>>;` : "";
	const overloads = contentTypeOverloads || observeOverloads;
	const observableDataType = isModelType ? "TData" : dataType;
	const singleImplementationReturnType = isRequestOptions ? `Observable<${observableDataType} | HttpEvent<${observableDataType}> | AngularHttpResponse<${observableDataType}>>` : `Observable<${observableDataType}>`;
	if (hasMultipleContentTypes) {
		const requiredProps = props.filter((p) => p.required && !p.default);
		const optionalProps = props.filter((p) => !p.required || p.default);
		const requiredPart = requiredProps.map((p) => p.implementation).join(",\n    ");
		const optionalPart = optionalProps.map((p) => p.implementation).join(",\n    ");
		return ` ${overloads}
  ${operationName}(
    ${[
			requiredPart,
			`accept: string = '${defaultContentType}'`,
			optionalPart
		].filter(Boolean).join(",\n    ")},
    ${isRequestOptions ? "options?: HttpClientOptions" : ""}
  ): ${multiImplementationReturnType} {${bodyForm}
    const headers = options?.headers instanceof HttpHeaders
      ? options.headers.set('Accept', accept)
      : { ...(options?.headers ?? {}), Accept: accept };

    if (accept.includes('json') || accept.includes('+json')) {
      return this.http.${verb}<${jsonReturnType}>(\`${route}\`, {
        ...options,
        responseType: 'json',
        headers,
      })${jsonValidationPipe};
    } else if (accept.startsWith('text/') || accept.includes('xml')) {
      return this.http.${verb}(\`${route}\`, {
        ...options,
        responseType: 'text',
        headers,
      }) as Observable<string>;
    } else {
      return this.http.${verb}(\`${route}\`, {
        ...options,
        responseType: 'blob',
        headers,
      }) as Observable<Blob>;
    }
  }
`;
	}
	const observeImplementation = isRequestOptions ? `${paramsDeclaration}if (options?.observe === 'events') {
      return this.http.${verb}${isModelType ? "<TData>" : ""}(${observeOptions?.events ?? options});
    }

    if (options?.observe === 'response') {
      return this.http.${verb}${isModelType ? "<TData>" : ""}(${observeOptions?.response ?? options});
    }

    return this.http.${verb}${isModelType ? "<TData>" : ""}(${observeOptions?.body ?? options})${validationPipe};` : `return this.http.${verb}${isModelType ? "<TData>" : ""}(${options})${validationPipe};`;
	return ` ${overloads}
  ${functionName}(
    ${toObjectString(props, "implementation")} ${isRequestOptions ? `options?: HttpClientOptions & { observe?: 'body' | 'events' | 'response' }` : ""}): ${singleImplementationReturnType} {${bodyForm}
    ${observeImplementation}
  }
`;
};
const createAngularClient = (returnTypesToWrite) => (verbOptions, options, _outputClient, _output) => {
	const isZodOutput = typeof options.context.output.schemas === "object" && options.context.output.schemas.type === "zod";
	const responseType = verbOptions.response.definition.success;
	const isPrimitiveResponse = isPrimitiveResponseType(responseType);
	const shouldUseRuntimeValidation = verbOptions.override.angular.runtimeValidation && isZodOutput;
	const normalizedVerbOptions = (() => {
		if (!shouldUseRuntimeValidation) return verbOptions;
		let result = verbOptions;
		if (!isPrimitiveResponse && hasSchemaImport(result.response.imports, responseType)) result = {
			...result,
			response: {
				...result.response,
				imports: result.response.imports.map((imp) => imp.name === responseType ? {
					...imp,
					values: true
				} : imp)
			}
		};
		const successTypes = result.response.types.success;
		if ([...new Set(successTypes.map((t) => t.contentType).filter(Boolean))].length > 1) {
			const jsonSchemaNames = [...new Set(successTypes.filter(({ contentType }) => !!contentType && (contentType.includes("json") || contentType.includes("+json"))).map(({ value }) => value))];
			if (jsonSchemaNames.length === 1) {
				const jsonType = jsonSchemaNames[0];
				if (!isPrimitiveResponseType(jsonType) && hasSchemaImport(result.response.imports, jsonType)) result = {
					...result,
					response: {
						...result.response,
						imports: result.response.imports.map((imp) => imp.name === jsonType ? {
							...imp,
							values: true
						} : imp)
					}
				};
			}
		}
		return result;
	})();
	const implementation = generateImplementation(returnTypesToWrite, normalizedVerbOptions, options);
	return {
		implementation,
		imports: [...generateVerbImports(normalizedVerbOptions), ...implementation.includes(".pipe(map(") ? [{
			name: "map",
			values: true,
			importPath: "rxjs"
		}] : []]
	};
};
const standaloneReturnTypesToWrite = /* @__PURE__ */ new Map();
const generateAngular = (verbOptions, options, outputClient, output) => createAngularClient(standaloneReturnTypesToWrite)(verbOptions, options, outputClient, output);
const createAngularClientBuilder = () => {
	const returnTypesToWrite = /* @__PURE__ */ new Map();
	return {
		client: createAngularClient(returnTypesToWrite),
		header: createAngularHeader(),
		dependencies: getAngularDependencies,
		footer: createAngularFooter(returnTypesToWrite),
		title: generateAngularTitle
	};
};
const builder = () => {
	return () => createAngularClientBuilder();
};

//#endregion
export { builder, builder as default, generateAngular, generateAngularFooter, generateAngularHeader, generateAngularTitle, getAngularDependencies };
//# sourceMappingURL=index.mjs.map