// ABOUTME: Drives every exercise audio player audio_player.py draws: play, skip, mute, seek, speed and the time shown.
// ABOUTME: Registered once however many times the page reruns; each player is found from the control that was used.

if (!window.__maniPlayer) {
  window.__maniPlayer = true;

  const clock = (seconds) => {
    const whole = Math.floor(seconds || 0);
    return Math.floor(whole / 60) + ":" + String(whole % 60).padStart(2, "0");
  };

  const partsOf = (element) => {
    const player = element.closest(".mani-player");
    return player && { player, audio: player.querySelector("audio"), seek: player.querySelector(".mani-seek") };
  };

  const draw = ({ player, audio, seek }) => {
    const total = audio.duration || 0;
    const done = total ? audio.currentTime / total : 0;
    seek.value = done * 1000;
    seek.style.setProperty("--p", done * 100 + "%");
    seek.setAttribute("aria-valuetext", clock(audio.currentTime) + " of " + clock(total));
    player.querySelector(".mani-time").textContent = clock(audio.currentTime) + " / " + clock(total);
    player.classList.toggle("is-playing", !audio.paused);
    player.classList.toggle("is-muted", audio.muted);
    player.querySelector("[data-act=play]").setAttribute("aria-label", audio.paused ? "Play" : "Pause");
    player.querySelector("[data-act=mute]").setAttribute("aria-label", audio.muted ? "Unmute" : "Mute");
    // A link that will not load, such as one past its hour, says so instead of ignoring taps.
    player.classList.toggle("is-broken", !!audio.error);
    if (audio.error) player.querySelector(".mani-time").textContent = "Audio unavailable right now. Reload the page.";
  };

  // Media events do not bubble, so they are caught on their way down to the audio element.
  for (const type of ["loadedmetadata", "timeupdate", "play", "pause", "ended", "volumechange", "error"]) {
    document.addEventListener(type, (event) => {
      const parts = event.target instanceof HTMLAudioElement && partsOf(event.target);
      if (parts) draw(parts);
    }, true);
  }

  const actions = {
    play: (audio) => (audio.paused ? audio.play() : audio.pause()),
    skip: (audio, button) => {
      audio.currentTime = Math.min(Math.max(audio.currentTime + Number(button.dataset.by), 0), audio.duration || 0);
    },
    mute: (audio) => { audio.muted = !audio.muted; },
  };

  document.addEventListener("click", (event) => {
    const button = event.target.closest(".mani-player [data-act]");
    if (button) actions[button.dataset.act](partsOf(button).audio, button);
  });

  document.addEventListener("input", (event) => {
    if (!event.target.matches(".mani-seek")) return;
    const parts = partsOf(event.target);
    if (parts.audio.duration) parts.audio.currentTime = (event.target.value / 1000) * parts.audio.duration;
    draw(parts);
  });

  document.addEventListener("change", (event) => {
    if (event.target.matches(".mani-speed")) partsOf(event.target).audio.playbackRate = Number(event.target.value);
  });
}
