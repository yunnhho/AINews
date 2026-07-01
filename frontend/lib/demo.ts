// 공개 읽기전용 데모 모드 플래그.
// NEXT_PUBLIC_DEMO_MODE=true 이면 Admin을 로그인 없이 열고 쓰기 버튼을 비활성화한다.
// (백엔드도 DEMO_MODE=true로 쓰기를 403 차단하므로 이중 안전장치)
export const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === 'true'
