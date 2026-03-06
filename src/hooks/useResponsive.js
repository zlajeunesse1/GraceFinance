/**
 * useResponsive — Screen size detection hook.
 *
 * Returns:
 *   isMobile: boolean (< 640px — phones)
 *   isTablet: boolean (640px - 1024px — tablets)
 *   isDesktop: boolean (> 1024px)
 *   width: number (current window width)
 *
 * Place at: src/hooks/useResponsive.js
 */

import { useState, useEffect } from "react"

export default function useResponsive() {
  var widthState = useState(
    typeof window !== "undefined" ? window.innerWidth : 1200
  )
  var width = widthState[0]
  var setWidth = widthState[1]

  useEffect(function () {
    function handleResize() {
      setWidth(window.innerWidth)
    }
    window.addEventListener("resize", handleResize)
    return function () {
      window.removeEventListener("resize", handleResize)
    }
  }, [])

  return {
    isMobile: width < 640,
    isTablet: width >= 640 && width <= 1024,
    isDesktop: width > 1024,
    width: width,
  }
}