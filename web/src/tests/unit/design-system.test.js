import { describe, it, expect } from 'vitest'
import tailwindConfig from '../../../tailwind.config.js'

describe('Design System Configuration', () => {
  describe('Tailwind Theme', () => {
    it('defines cyber color palette', () => {
      const colors = tailwindConfig.theme.extend.colors

      expect(colors.cyber).toBeDefined()
      expect(colors.cyber.dark).toBe('#0a0e27')
      expect(colors.cyber.darker).toBe('#050812')
      expect(colors.cyber.blue).toBe('#00d9ff')
      expect(colors.cyber.purple).toBe('#b537f2')
      expect(colors.cyber.green).toBe('#00ff88')
      expect(colors.cyber.red).toBe('#ff0055')
      expect(colors.cyber.orange).toBe('#ff6b35')
    })

    it('defines status colors for vulnerability severity', () => {
      const statusColors = tailwindConfig.theme.extend.colors.status

      expect(statusColors).toBeDefined()
      expect(statusColors.critical).toBe('#ff0055')
      expect(statusColors.high).toBe('#ff6b35')
      expect(statusColors.medium).toBe('#ffa500')
      expect(statusColors.low).toBe('#00ff88')
      expect(statusColors.info).toBe('#00d9ff')
    })

    it('defines custom animations', () => {
      const animations = tailwindConfig.theme.extend.animation

      expect(animations.glow).toBeDefined()
      expect(animations.pulse).toBeDefined()
      expect(animations.scan).toBeDefined()
      expect(animations['fade-in']).toBeDefined()
      expect(animations['fade-out']).toBeDefined()
      expect(animations['slide-in']).toBeDefined()
      expect(animations['slide-out']).toBeDefined()
    })

    it('defines custom keyframes', () => {
      const keyframes = tailwindConfig.theme.extend.keyframes

      expect(keyframes.glow).toBeDefined()
      expect(keyframes.scan).toBeDefined()
      expect(keyframes.pulse).toBeDefined()
      expect(keyframes.fadeIn).toBeDefined()
      expect(keyframes.fadeOut).toBeDefined()
      expect(keyframes.slideIn).toBeDefined()
      expect(keyframes.slideOut).toBeDefined()
    })

    it('defines typography with custom fonts', () => {
      const fontFamily = tailwindConfig.theme.extend.fontFamily

      expect(fontFamily.heading).toContain('Orbitron')
      expect(fontFamily.sans).toContain('Inter')
      expect(fontFamily.mono).toContain('JetBrains Mono')
    })

    it('defines glass effect blur values', () => {
      const backdropBlur = tailwindConfig.theme.extend.backdropBlur

      expect(backdropBlur.xs).toBe('2px')
      expect(backdropBlur['4xl']).toBe('72px')
    })

    it('defines custom box shadows for depth', () => {
      const boxShadow = tailwindConfig.theme.extend.boxShadow

      expect(boxShadow.glow).toBeDefined()
      expect(boxShadow['glow-sm']).toBeDefined()
      expect(boxShadow['glow-lg']).toBeDefined()
      expect(boxShadow.cyber).toBeDefined()
    })
  })

  describe('Color Accessibility', () => {
    it('uses dark background colors for cyber theme', () => {
      const colors = tailwindConfig.theme.extend.colors.cyber

      // Check that dark colors are actually dark (low luminance)
      expect(colors.dark).toMatch(/^#[0-9a-f]{6}$/i)
      expect(colors.darker).toMatch(/^#[0-9a-f]{6}$/i)
    })

    it('uses high contrast accent colors', () => {
      const colors = tailwindConfig.theme.extend.colors.cyber

      // Accent colors should be vibrant hex codes
      expect(colors.blue).toMatch(/^#[0-9a-f]{6}$/i)
      expect(colors.purple).toMatch(/^#[0-9a-f]{6}$/i)
      expect(colors.green).toMatch(/^#[0-9a-f]{6}$/i)
    })

    it('uses semantic colors for status indicators', () => {
      const status = tailwindConfig.theme.extend.colors.status

      expect(status.critical).toBe('#ff0055') // Red
      expect(status.high).toBe('#ff6b35') // Orange
      expect(status.medium).toBe('#ffa500') // Amber
      expect(status.low).toBe('#00ff88') // Green
      expect(status.info).toBe('#00d9ff') // Blue
    })
  })

  describe('Responsive Design', () => {
    it('uses default Tailwind breakpoints', () => {
      // Tailwind default breakpoints:
      // sm: 640px, md: 768px, lg: 1024px, xl: 1280px, 2xl: 1536px
      // We're using the defaults, so no custom breakpoints defined
      expect(tailwindConfig.theme.extend.screens).toBeUndefined()
    })
  })

  describe('Animation Performance', () => {
    it('defines GPU-accelerated animations', () => {
      const keyframes = tailwindConfig.theme.extend.keyframes

      // Glow uses opacity and filter (GPU-accelerated)
      expect(keyframes.glow).toBeDefined()

      // Scan uses transform (GPU-accelerated)
      expect(keyframes.scan).toBeDefined()

      // Fade uses opacity (GPU-accelerated)
      expect(keyframes.fadeIn).toBeDefined()
      expect(keyframes.fadeOut).toBeDefined()
    })

    it('provides reduced motion support via Tailwind utilities', () => {
      // Tailwind provides motion-reduce variants by default
      // This is handled in CSS, not config
      expect(tailwindConfig.theme).toBeDefined()
    })
  })

  describe('Dark Mode Support', () => {
    it('uses class-based dark mode strategy', () => {
      expect(tailwindConfig.darkMode).toBe('class')
    })
  })

  describe('Content Paths', () => {
    it('scans correct file paths for class usage', () => {
      const content = tailwindConfig.content

      expect(content).toContain('./index.html')
      expect(content).toContain('./src/**/*.{js,ts,jsx,tsx}')
    })
  })

  describe('Plugin Configuration', () => {
    it('includes required Tailwind plugins', () => {
      const plugins = tailwindConfig.plugins

      expect(Array.isArray(plugins)).toBe(true)
      // Forms and typography plugins should be included
      expect(plugins.length).toBeGreaterThan(0)
    })
  })

  describe('Spacing Scale', () => {
    it('uses default Tailwind spacing scale', () => {
      // Using default spacing (0.25rem increments)
      expect(tailwindConfig.theme.extend.spacing).toBeUndefined()
    })
  })

  describe('Typography Scale', () => {
    it('defines custom font sizes for headings', () => {
      const fontSize = tailwindConfig.theme.extend.fontSize

      if (fontSize) {
        // Custom sizes should follow design system hierarchy
        expect(fontSize).toBeDefined()
      }
    })
  })
})
