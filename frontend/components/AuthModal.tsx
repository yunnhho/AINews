'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import SocialLoginButtons from './SocialLoginButtons'

interface Props {
  open: boolean
  onClose: () => void
}

export default function AuthModal({ open, onClose }: Props) {
  // 헤더에 backdrop-filter가 걸려 있어 그 내부에서 렌더하면 position:fixed가
  // 헤더를 기준으로 잡힌다. document.body로 포털해 뷰포트 기준으로 띄운다.
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  // 열렸을 때 ESC 닫기 + 배경 스크롤 잠금
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [open, onClose])

  if (!mounted) return null

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 bg-black/40"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ type: 'spring', damping: 30, stiffness: 340 }}
            role="dialog"
            aria-modal="true"
            className="relative z-10 w-full max-w-sm bg-paper border-2 border-ink px-6 pt-6 pb-8"
          >
            <div className="label-kicker text-accent text-center mb-3">Members Only</div>
            <h2 className="font-serif text-2xl font-extrabold text-ink text-center mb-1.5 tracking-[-0.01em]">
              로그인이 필요합니다
            </h2>
            <p className="text-sm text-ink-soft text-center mb-6">
              좋아요·북마크는 로그인 후 이용할 수 있어요.
            </p>
            <SocialLoginButtons />
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
