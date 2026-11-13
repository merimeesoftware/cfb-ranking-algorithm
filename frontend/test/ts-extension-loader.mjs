/**
 * Node's type stripper does not add .ts for extensionless imports.
 * App code keeps the extensionless form Vite already uses.
 */
export async function resolve(specifier, context, nextResolve) {
	if (specifier.startsWith('.') && !/\.[cm]?[jt]s$/.test(specifier)) {
		return nextResolve(`${specifier}.ts`, context);
	}
	return nextResolve(specifier, context);
}
