/**
 * Короткие звуки обратной связи.
 *
 * Генерируем через WebAudio, а не тянем mp3: файл пришлось бы грузить, кэшировать
 * и лицензировать, а тут два тона в пару строк. Контекст создаём лениво —
 * браузер не даёт запускать звук до первого действия пользователя.
 */

const STORAGE_KEY = "botalka_sound";

let ctx: AudioContext | null = null;

function context(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
  }
  return ctx;
}

export function soundEnabled(): boolean {
  if (typeof window === "undefined") return true;
  return window.localStorage.getItem(STORAGE_KEY) !== "off";
}

export function setSoundEnabled(on: boolean): void {
  window.localStorage.setItem(STORAGE_KEY, on ? "on" : "off");
}

function tone(frequency: number, startAt: number, duration: number, volume: number): void {
  const audio = context();
  if (!audio) return;

  const oscillator = audio.createOscillator();
  const gain = audio.createGain();

  oscillator.type = "sine";
  oscillator.frequency.value = frequency;

  // мягкая огибающая: резкий старт звучит как щелчок
  gain.gain.setValueAtTime(0, audio.currentTime + startAt);
  gain.gain.linearRampToValueAtTime(volume, audio.currentTime + startAt + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + startAt + duration);

  oscillator.connect(gain).connect(audio.destination);
  oscillator.start(audio.currentTime + startAt);
  oscillator.stop(audio.currentTime + startAt + duration + 0.05);
}

/** Одобрительная секунда вверх — играет при верном ответе. */
export function playCorrect(): void {
  if (!soundEnabled()) return;
  tone(660, 0, 0.14, 0.16);     // ми
  tone(880, 0.1, 0.22, 0.14);   // ля
}

/** Глухой короткий тон на ошибку — тише и ниже, чтобы не раздражал. */
export function playWrong(): void {
  if (!soundEnabled()) return;
  tone(210, 0, 0.2, 0.09);
}
