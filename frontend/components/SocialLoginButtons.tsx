const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/v1'

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  )
}

function GitHubIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
    </svg>
  )
}

function KakaoIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="#000000">
      <path d="M12 3C6.477 3 2 6.463 2 10.735c0 2.764 1.85 5.187 4.63 6.55-.205.74-.74 2.68-.847 3.097-.133.516.19.51.4.37.164-.108 2.6-1.766 3.65-2.48.708.103 1.434.158 2.167.158 5.523 0 10-3.463 10-7.735C22 6.463 17.523 3 12 3z"/>
    </svg>
  )
}

export default function SocialLoginButtons() {
  return (
    <div className="flex flex-col gap-3">
      <a
        href={`${API_BASE}/auth/google`}
        className="flex items-center justify-center gap-3 w-full px-4 py-3 bg-white border border-gray-300 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <GoogleIcon />
        Google로 계속하기
      </a>
      <a
        href={`${API_BASE}/auth/github`}
        className="flex items-center justify-center gap-3 w-full px-4 py-3 bg-gray-900 rounded-xl text-sm font-medium text-white hover:bg-gray-800 transition-colors"
      >
        <GitHubIcon />
        GitHub로 계속하기
      </a>
      <a
        href={`${API_BASE}/auth/kakao`}
        className="flex items-center justify-center gap-3 w-full px-4 py-3 bg-[#FEE500] rounded-xl text-sm font-medium text-[#191600] hover:brightness-95 transition-all"
      >
        <KakaoIcon />
        카카오로 계속하기
      </a>
    </div>
  )
}
