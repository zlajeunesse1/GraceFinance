/**
 * GraceFinance - useProfile hook
 * Load, save, optimistic update, error handling.
 * Drop into any component that needs profile data.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { profileApi } from '../api/profile'

export function useProfile() {
  const [profile, setProfile] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState(null)
  const [saveError, setSaveError] = useState(null)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  const fetchProfile = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await profileApi.get()
      if (mounted.current) setProfile(data)
    } catch (err) {
      if (mounted.current) setError(err.message || 'Failed to load profile')
    } finally {
      if (mounted.current) setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchProfile()
  }, [fetchProfile])

  const updateProfile = useCallback(async (payload) => {
    if (!profile) return
    setSaveError(null)
    setIsSaving(true)

    // Optimistic update
    const previous = profile
    setProfile((prev) => ({ ...prev, ...payload }))

    try {
      const updated = await profileApi.update(payload)
      if (mounted.current) setProfile(updated)
    } catch (err) {
      // Roll back on failure
      if (mounted.current) {
        setProfile(previous)
        setSaveError(err.message || 'Failed to save profile')
      }
    } finally {
      if (mounted.current) setIsSaving(false)
    }
  }, [profile])

  return { profile, isLoading, isSaving, error, saveError, updateProfile, refetch: fetchProfile }
}