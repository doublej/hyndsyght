<script lang="ts">
  import '../lib/styles/global.css'
  import Nav from '$lib/components/Nav.svelte'
  import { plate } from '$lib/theme'
  let { children } = $props()

  // html:root outranks the fallback :root in global.css, whatever order the tags land in
  const plateVars = `html:root{--plate-l:${plate.l};--plate-c:${plate.c};--hue:${plate.h}}`
  const plateColor = `oklch(${plate.l} ${plate.c} ${plate.h})`
</script>

<svelte:head>
  {@html `<style>${plateVars}</style>`}
  <meta name="theme-color" content={plateColor} />
</svelte:head>

<Nav />
{@render children()}
