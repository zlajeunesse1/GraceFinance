/**
 * GraceFinance - useProfile hook (v6.1)
 * Load, save, optimistic update, error handling.
 * Drop into any component that needs profile data.
 *
 * CHANGES FROM v6:
 *   - FIX: updateProfile now RETURNS the server response on success (or null on failure)
 *          so callers can check whether the save actually persisted
 *   - Convention: var declarations, function expressions (matches codebase)
 */

import { useState, useEffect, useCallback, useRef } from "react"
import { profileApi } from "../api/profile"

export function useProfile() {
  var profileState = useState(null); var profile = profileState[0]; var setProfile = profileState[1]
  var loadingState = useState(true); var isLoading = loadingState[0]; var setIsLoading = loadingState[1]
  var savingState = useState(false); var isSaving = savingState[0]; var setIsSaving = savingState[1]
  var errorState = useState(null); var error = errorState[0]; var setError = errorState[1]
  var saveErrorState = useState(null); var saveError = saveErrorState[0]; var setSaveError = saveErrorState[1]
  var mounted = useRef(true)

  useEffect(function () {
    mounted.current = true
    return function () { mounted.current = false }
  }, [])

  var fetchProfile = useCallback(function () {
    setIsLoading(true)
    setError(null)
    return profileApi.get()
      .then(function (data) {
        if (mounted.current) setProfile(data)
      })
      .catch(function (err) {
        if (mounted.current) setError(err.message || "Failed to load profile")
      })
      .finally(function () {
        if (mounted.current) setIsLoading(false)
      })
  }, [])

  useEffect(function () {
    fetchProfile()
  }, [fetchProfile])

  /**
   * updateProfile — sends PATCH to backend.
   * Returns the server response on success so callers can verify what persisted.
   * Returns null on failure (and sets saveError).
   */
  var updateProfile = useCallback(function (payload) {
    if (!profile) return Promise.resolve(null)
    setSaveError(null)
    setIsSaving(true)

    /* Optimistic update */
    var previous = profile
    setProfile(function (prev) {
      var merged = {}
      for (var key in prev) { merged[key] = prev[key] }
      for (var key2 in payload) { merged[key2] = payload[key2] }
      return merged
    })

    return profileApi.update(payload)
      .then(function (updated) {
        if (mounted.current) setProfile(updated)
        return updated  /* Return server response so caller can verify */
      })
      .catch(function (err) {
        /* Roll back on failure */
        if (mounted.current) {
          setProfile(previous)
          setSaveError(err.message || "Failed to save profile")
        }
        return null  /* Signal failure to caller */
      })
      .finally(function () {
        if (mounted.current) setIsSaving(false)
      })
  }, [profile])

  return {
    profile: profile,
    isLoading: isLoading,
    isSaving: isSaving,
    error: error,
    saveError: saveError,
    updateProfile: updateProfile,
    refetch: fetchProfile,
  }
}