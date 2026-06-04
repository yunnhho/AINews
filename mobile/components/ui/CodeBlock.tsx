import { ScrollView } from 'react-native'
// @ts-ignore — no types for this package
import SyntaxHighlighter from 'react-native-syntax-highlighter'
// @ts-ignore
import { atomOneDark } from 'react-syntax-highlighter/dist/styles/hljs'

interface Props {
  code: string
  language?: string
}

// 신뢰할 수 없는 외부 code_snippet을 하이라이팅하므로, 과도하게 긴 입력으로 인한
// 정규식 백트래킹(ReDoS)·UI 프리즈를 막기 위해 길이를 제한한다.
const MAX_CODE_LEN = 10_000

function detectLanguage(code: string): string {
  if (code.includes('def ') || code.includes('import ') && code.includes(':')) return 'python'
  if (code.includes('const ') || code.includes('=>') || code.includes('function ')) return 'javascript'
  if (code.includes('fn ') && code.includes('->')) return 'rust'
  if (code.includes('func ') && code.includes('go ')) return 'go'
  return 'python'
}

export function CodeBlock({ code, language }: Props) {
  const safeCode = code.length > MAX_CODE_LEN ? code.slice(0, MAX_CODE_LEN) + '\n…' : code
  const lang = language ?? detectLanguage(safeCode)

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} className="rounded-xl">
      <SyntaxHighlighter
        language={lang}
        style={atomOneDark}
        customStyle={{ borderRadius: 12, padding: 12, margin: 0 }}
        fontSize={12}
      >
        {safeCode}
      </SyntaxHighlighter>
    </ScrollView>
  )
}
