export function isBraveBrowser(): boolean {
  const navigatorWithBrave = navigator as Navigator & {
    brave?: { isBrave?: () => Promise<boolean> | boolean };
  };

  if (!navigatorWithBrave.brave?.isBrave) {
    return false;
  }

  try {
    const result = navigatorWithBrave.brave.isBrave();
    return typeof result === 'boolean' ? result : false;
  } catch {
    return false;
  }
}

export async function shouldPreferBackendVoice(): Promise<boolean> {
  if (isBraveBrowser()) return true;

  const navigatorWithBrave = navigator as Navigator & {
    brave?: { isBrave?: () => Promise<boolean> | boolean };
  };

  if (navigatorWithBrave.brave?.isBrave) {
    const result = await navigatorWithBrave.brave.isBrave();
    if (result) return true;
  }

  return false;
}
