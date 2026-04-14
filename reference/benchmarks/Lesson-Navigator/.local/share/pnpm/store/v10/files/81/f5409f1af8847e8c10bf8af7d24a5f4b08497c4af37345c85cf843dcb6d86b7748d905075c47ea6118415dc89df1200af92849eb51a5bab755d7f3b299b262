/**
 * Utility for enforcing exhaustiveness checks in the type system.
 *
 * @see https://basarat.gitbook.io/typescript/type-system/discriminated-unions#throw-in-exhaustive-checks
 *
 * @param value The variable with no remaining values
 */
export declare function assertNever(value: never): never;
type AllKeys<T> = T extends unknown ? keyof T : never;
export declare function pick<O, K extends AllKeys<O>>(base: O, keys: readonly K[]): Pick<O, K>;
export declare function isObject(o: unknown): o is Record<PropertyKey, unknown>;
export type EndpointDefinition = {
    pathParams: readonly string[];
    queryParams: readonly string[];
    bodyParams: readonly string[];
    formDataParams?: readonly string[];
};
/**
 * Returns parameter names present in `args` that are not recognized by the
 * endpoint definition. Useful for warning users about typos or parameters
 * that have been renamed across API versions.
 */
export declare function getUnknownParams(args: Record<string, unknown>, endpoint: EndpointDefinition): string[];
export {};
//# sourceMappingURL=utils.d.ts.map