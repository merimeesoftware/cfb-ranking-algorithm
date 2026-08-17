<script lang="ts">
	import { BRAND_NAME, SITE_ORIGIN, TAGLINE } from '$lib/brand';

	export let title: string = BRAND_NAME;
	export let description: string = `${BRAND_NAME} — ${TAGLINE}`;
	export let canonicalPath: string = '/';
	export let ogType: string = 'website';
	export let jsonLd: Record<string, unknown> | Record<string, unknown>[] | null = null;

	$: canonical = `${SITE_ORIGIN}${canonicalPath.startsWith('/') ? canonicalPath : `/${canonicalPath}`}`;
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={canonical} />
	<meta property="og:site_name" content={BRAND_NAME} />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
	<meta property="og:type" content={ogType} />
	<meta property="og:url" content={canonical} />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content={title} />
	<meta name="twitter:description" content={description} />
	{#if jsonLd}
		{@html `<script type="application/ld+json">${JSON.stringify(jsonLd).replace(/</g, '\\u003c')}</script>`}
	{/if}
</svelte:head>
