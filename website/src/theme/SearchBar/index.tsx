/**
 * Swizzle of @theme/SearchBar. Replaces Algolia DocSearch with the local
 * index-backed search in src/components/SiteSearch.
 *
 * SiteSearch already handles its own failure mode (a failed index fetch shows a
 * message rather than throwing), so no error boundary wrapper is needed here.
 */
import React from 'react';
import SiteSearch from '@site/src/components/SiteSearch';

export default function SearchBarWrapper(): React.JSX.Element {
  return <SiteSearch />;
}
