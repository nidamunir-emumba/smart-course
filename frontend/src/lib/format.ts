const DATE_FMT = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
})

export function formatDate(iso: string): string {
  return DATE_FMT.format(new Date(iso))
}
