'use client'

import { useEffect, useState } from 'react'

function guessLang(code: string): string {
  if (/^\s*(def |class |import |from |async def |@\w)/.test(code)) return 'python'
  if (/^\s*(const |let |var |function |export |import \{|=>)/.test(code)) return 'typescript'
  if (/^\s*(#!\/|apt|npm |pip |cargo |kubectl |docker |git )/.test(code)) return 'bash'
  if (/^\s*\{[\s\S]*"/.test(code)) return 'json'
  if (/^\s*(- |\w+:)/.test(code)) return 'yaml'
  return 'text'
}

interface Props {
  code: string
  lang?: string
}

export default function CodeBlock({ code, lang }: Props) {
  const [html, setHtml] = useState<string | null>(null)
  const resolvedLang = lang ?? guessLang(code)

  useEffect(() => {
    let cancelled = false
    import('shiki')
      .then(({ codeToHtml }) =>
        codeToHtml(code, { lang: resolvedLang, theme: 'github-light' }),
      )
      .then((result) => {
        if (!cancelled) setHtml(result)
      })
      .catch(() => {
        // Shiki 로드 실패 시 plain fallback 유지
      })
    return () => {
      cancelled = true
    }
  }, [code, resolvedLang])

  if (html === null) {
    return (
      <pre className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs overflow-x-auto font-mono leading-relaxed">
        <code>{code}</code>
      </pre>
    )
  }

  return (
    <div
      className="text-xs rounded-lg overflow-x-auto border border-gray-200 [&>pre]:!m-0 [&>pre]:!rounded-lg [&>pre]:!p-3 [&>pre]:font-mono [&>pre]:leading-relaxed"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
