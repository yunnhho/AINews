'use client'

import { AnimatePresence, motion } from 'framer-motion'
import SocialLoginButtons from './SocialLoginButtons'

interface Props {
  open: boolean
  onClose: () => void
}

export default function AuthModal({ open, onClose }: Props) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 bg-black/40 z-50"
            onClick={onClose}
          />
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 32, stiffness: 320 }}
            className="fixed bottom-0 inset-x-0 z-50 bg-white rounded-t-2xl px-6 pt-4 pb-10 max-w-lg mx-auto shadow-2xl"
          >
            <div className="w-10 h-1 bg-gray-200 rounded-full mx-auto mb-5" />
            <h2 className="text-lg font-semibold text-gray-900 text-center mb-1.5">
              로그인이 필요합니다
            </h2>
            <p className="text-sm text-gray-500 text-center mb-6">
              좋아요·북마크는 로그인 후 이용할 수 있어요.
            </p>
            <SocialLoginButtons />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
