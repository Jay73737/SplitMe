export class AudioAnalyzer {
  constructor() {
    this.audioContext = null;
    this.audioBuffer = null;
  }

  async initializeAudioContext() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();
    }

    if (this.audioContext.state === "suspended") {
      await this.audioContext.resume();
    }

    return this.audioContext;
  }

  async analyzeYouTubeVideo(videoId) {
    try {
      const audioUrl = await this.getYouTubeAudioUrl(videoId);
      if (!audioUrl) {
        throw new Error("Could not get audio URL from YouTube video");
      }

      const audioBuffer = await this.fetchAndDecodeAudio(audioUrl);
      return this.generateWaveformData(audioBuffer);
    } catch (error) {
      console.warn("Failed to analyze YouTube audio:", error);

      const fallback = await this.generateFallbackAudioBuffer();
      return this.generateWaveformData(fallback);
    }
  }

  async testPipedAPI() {
    const testVideoId = 'dQw4w9WgXcQ';
    console.log('Testing Piped API with known working video:', testVideoId);
    return await this.getYouTubeAudioUrl(testVideoId);
  }

  async checkServiceStatus() {
    console.log('Checking audio extraction service status...');
    const result = await this.testPipedAPI();
    if (result) {
      console.log('✅ Audio extraction services are working');
      return { status: 'working', message: 'Services operational' };
    } else {
      console.log('❌ Audio extraction services are currently unavailable');
      return { 
        status: 'unavailable', 
        message: 'Third-party YouTube audio extraction services (Piped/Invidious) are currently experiencing issues. This is common and usually resolves within a few hours. Try again later or use videos from independent creators which are less likely to be geo-blocked.' 
      };
    }
  }

  async getYouTubeAudioUrl(videoId) {
    const pipedInstances = [
      'https://pipedapi.syncpundit.io',
      'https://pipedapi.palvelukeskus.eu', 
      'https://api-piped.mha.fi',
      'https://pipedapi.smnz.de',
      'https://pipedapi.privacy.com.de',
      'https://api.piped.privacydev.net',
      'https://pipedapi.kavin.rocks',
      'https://pipedapi.leptons.xyz', 
      'https://api.piped.yt',
      'https://pipedapi-libre.kavin.rocks',
      'https://piapi.ggtyler.dev',
      'https://pipedapi.adminforge.de',
      'https://api.piped.projectsegfau.lt'
    ];

    for (const instance of pipedInstances) {
      try {
        const apiUrl = `${instance}/streams/${videoId}`;
        console.log("Trying Piped instance:", apiUrl);
        
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch(apiUrl, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
          },
          signal: controller.signal
        });
        
        clearTimeout(timeout);
        
        if (!response.ok) {
          console.warn(`Piped instance ${instance} failed: HTTP ${response.status} - ${response.statusText}`);
          continue;
        }
        
        const data = await response.json();
        
        const audioStreams = data?.audioStreams || [];
        console.log(`Found ${audioStreams.length} audio streams from ${instance}`);
        
        if (audioStreams.length > 0) {
          const sortedStreams = audioStreams.sort((a, b) => {
            if (a.mimeType?.includes('webm') && !b.mimeType?.includes('webm')) return -1;
            if (!a.mimeType?.includes('webm') && b.mimeType?.includes('webm')) return 1;
            return (a.bitrate || 0) - (b.bitrate || 0);
          });
          
          const audio = sortedStreams[0]?.url;
          if (audio) {
            console.log("Successfully got audio URL from", instance, ":", audio, 
                       "- format:", sortedStreams[0].mimeType, "- bitrate:", sortedStreams[0].bitrate);
            return audio;
          }
        }
        
        console.warn("No usable audio streams found in response from", instance);
        if (data?.error) {
          console.warn("API error:", data.error);
        } else {
          console.warn("Response structure:", {
            hasAudioStreams: !!data?.audioStreams,
            streamCount: data?.audioStreams?.length || 0,
            videoTitle: data?.title,
            duration: data?.duration
          });
        }
      } catch (error) {
        if (error.name === 'AbortError') {
          console.warn(`Piped instance ${instance} timed out after 5 seconds`);
        } else {
          console.warn(`Error with Piped instance ${instance}:`, error.message || error);
        }
        continue;
      }
    }
    
    console.warn("All Piped instances failed for video:", videoId);
    
    console.log("Attempting alternative YouTube audio extraction...");
    return await this.getYouTubeAudioUrlAlternative(videoId);
  }

  async getYouTubeAudioUrlAlternative(videoId) {
    try {
      const invidiousInstances = [
        'https://inv.nadeko.net',
        'https://invidious.snopyta.org',
        'https://yewtu.be',
        'https://invidious.kavin.rocks',
        'https://vid.puffyan.us'
      ];

      for (const instance of invidiousInstances) {
        try {
          console.log(`Trying Invidious instance: ${instance}`);
          const apiUrl = `${instance}/api/v1/videos/${videoId}`;
          
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), 5000);
          
          const response = await fetch(apiUrl, {
            signal: controller.signal,
            headers: {
              'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
          });
          
          clearTimeout(timeout);
          
          if (!response.ok) {
            console.warn(`Invidious instance ${instance} failed: HTTP ${response.status}`);
            continue;
          }
          
          const data = await response.json();
          const audioFormats = data?.adaptiveFormats?.filter(f => 
            f.type?.includes('audio') && f.url
          ) || [];
          
          if (audioFormats.length > 0) {
            const webmAudio = audioFormats.find(f => f.type?.includes('webm'));
            const selectedFormat = webmAudio || audioFormats[0];
            console.log(`Found audio from Invidious: ${selectedFormat.url}`);
            return selectedFormat.url;
          }
          
        } catch (error) {
          console.warn(`Invidious instance ${instance} error:`, error.message);
          continue;
        }
      }
      
      console.warn("All Invidious instances failed");
      return null;
      
    } catch (error) {
      console.warn("Alternative audio extraction failed:", error);
      return null;
    }
  }

  async fetchAndDecodeAudio(audioUrl) {
    const context = await this.initializeAudioContext();

    const response = await fetch(audioUrl);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const arrayBuffer = await response.arrayBuffer();
    const audioBuffer = await context.decodeAudioData(arrayBuffer);

    this.audioBuffer = audioBuffer;
    return audioBuffer;
  }

  async generateFallbackAudioBuffer(duration = 2) {
    const context = await this.initializeAudioContext();
    const sampleRate = context.sampleRate;
    const frameCount = Math.floor(sampleRate * duration);
    const buffer = context.createBuffer(1, frameCount, sampleRate);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < frameCount; i++) {
      const t = i / frameCount;
      const bass = Math.sin(2 * Math.PI * t) * 0.3;
      const mid = Math.sin(2 * Math.PI * 4 * t) * 0.2;
      const noise = (Math.random() - 0.5) * 0.1;
      data[i] = bass + mid + noise;
    }

    this.audioBuffer = buffer;
    return buffer;
  }

  generateWaveformData(audioBuffer, sampleCount = 200) {
    if (!audioBuffer) return this.generateFallbackWaveform();

    const channelData = audioBuffer.getChannelData(0);
    const samplesPerGroup = Math.floor(channelData.length / sampleCount);
    const waveformData = [];

    for (let i = 0; i < sampleCount; i++) {
      let sum = 0;
      let maxVal = 0;

      const start = i * samplesPerGroup;
      const end = Math.min(start + samplesPerGroup, channelData.length);

      for (let j = start; j < end; j++) {
        const sample = channelData[j];
        sum += sample * sample;
        maxVal = Math.max(maxVal, Math.abs(sample));
      }

      const rms = Math.sqrt(sum / (end - start));
      const amplitude = Math.max(rms, maxVal * 0.3);

      waveformData.push({
        amplitude: amplitude,
        position: i / sampleCount,
      });
    }

    return waveformData;
  }

  generateFallbackWaveform(sampleCount = 200) {
    const waveformData = [];

    for (let i = 0; i < sampleCount; i++) {
      const t = i / sampleCount;

      const bassFreq = Math.sin(t * Math.PI * 2) * 0.3;
      const midFreq = Math.sin(t * Math.PI * 8 + 1) * 0.4;
      const highFreq = Math.sin(t * Math.PI * 16 + 2) * 0.2;
      const noise = (Math.random() - 0.5) * 0.1;

      let envelope = 1;
      if (t < 0.1) envelope = t / 0.1;
      else if (t > 0.9) envelope = (1 - t) / 0.1;
      else envelope = 0.5 + 0.5 * Math.sin(t * Math.PI * 3);

      const amplitude =
        Math.abs(bassFreq + midFreq + highFreq + noise) * envelope;

      waveformData.push({
        amplitude: Math.min(amplitude, 1),
        position: t,
      });
    }

    return waveformData;
  }

  async analyzeFromYouTubePlayer(player) {
    if (!player || typeof player.getVideoData !== "function") {
      return this.generateFallbackWaveform();
    }

    try {
      await this.initializeAudioContext();

      const iframe = player.getIframe?.();
      if (iframe && iframe.contentWindow) {
        return this.generateFallbackWaveform();
      }
    } catch (error) {
      console.warn("Could not analyze YouTube player audio:", error);
    }

    return this.generateFallbackWaveform();
  }

  convertToSVGPath(waveformData, width = 740, height = 180) {
    if (!waveformData || waveformData.length === 0) {
      return { d: "", W: width, H: height, mid: height / 2 };
    }

    const mid = height / 2;
    let d = `M 0 ${mid}`;

    waveformData.forEach((point) => {
      const x = (point.position * width).toFixed(1);
      const amplitude = point.amplitude * (mid - 10);
      const y = (mid - amplitude).toFixed(1);
      d += ` L ${x} ${y}`;
    });

    for (let i = waveformData.length - 1; i >= 0; i--) {
      const point = waveformData[i];
      const x = (point.position * width).toFixed(1);
      const amplitude = point.amplitude * (mid - 10);
      const y = (mid + amplitude).toFixed(1);
      d += ` L ${x} ${y}`;
    }

    d += " Z";

    return { d, W: width, H: height, mid };
  }

  // Convert AudioBuffer to WAV ArrayBuffer for export or blob creation.
  audioBufferToWavArrayBuffer(buffer) {
    const length = buffer.length;
    const numberOfChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const arrayBuffer = new ArrayBuffer(44 + length * numberOfChannels * 2);
    const view = new DataView(arrayBuffer);
    
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * numberOfChannels * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numberOfChannels * 2, true);
    view.setUint16(32, numberOfChannels * 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length * numberOfChannels * 2, true);
    
    let offset = 44;
    for (let i = 0; i < length; i++) {
      for (let channel = 0; channel < numberOfChannels; channel++) {
        const sample = buffer.getChannelData(channel)[i];
        const intSample = Math.max(-1, Math.min(1, sample)) * 0x7FFF;
        view.setInt16(offset, intSample, true);
        offset += 2;
      }
    }
    
    return arrayBuffer;
  }

  // Convert AudioBuffer to WAV blob for WaveSurfer
  audioBufferToWav(buffer) {
    const arrayBuffer = this.audioBufferToWavArrayBuffer(buffer);
    return new Blob([arrayBuffer], { type: 'audio/wav' });
  }
}

export const audioAnalyzer = new AudioAnalyzer();
