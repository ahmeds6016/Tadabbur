# TypeScript Migration Guide

## ✅ TypeScript Setup Complete!

TypeScript has been successfully configured for your Tafsir Simplified application.

## 📁 New TypeScript Files Created

```
frontend/
├── tsconfig.json                 # TypeScript configuration
├── next-env.d.ts                 # Next.js TypeScript declarations
├── app/
│   ├── types/
│   │   └── index.ts             # All type definitions
│   ├── services/
│   │   └── tafsirApi.ts         # TypeScript version of API service
│   ├── components/
│   │   └── Logo.tsx             # New logo component with TypeScript
│   └── logo-demo/
│       └── page.tsx             # Demo page showing logo usage
```

## 🔄 How to Migrate Existing Files

### 1. Rename `.js` / `.jsx` files to `.ts` / `.tsx`

```bash
# For components (React files)
mv app/components/SomeComponent.jsx app/components/SomeComponent.tsx

# For utilities/services (non-React files)
mv app/utils/someUtil.js app/utils/someUtil.ts
```

### 2. Add Type Annotations

#### Before (JavaScript):
```javascript
export function SearchBar({ onSearch, initialQuery, isLoading }) {
  // ...
}
```

#### After (TypeScript):
```typescript
interface SearchBarProps {
  onSearch: (query: SearchQuery) => void;
  initialQuery?: string;
  isLoading?: boolean;
}

export function SearchBar({
  onSearch,
  initialQuery = '',
  isLoading = false
}: SearchBarProps) {
  // ...
}
```

### 3. Import Types

```typescript
// Import types from the central types file
import type { User, UserProfile, TafsirResponse } from '@/types';

// Use in your components
const [user, setUser] = useState<User | null>(null);
const [response, setResponse] = useState<TafsirResponse | null>(null);
```

### 4. Update Event Handlers

#### Before:
```javascript
const handleSubmit = (e) => {
  e.preventDefault();
  // ...
}
```

#### After:
```typescript
const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  // ...
}

// Or for input changes:
const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  setValue(e.target.value);
}
```

## 📝 Common TypeScript Patterns for Your App

### State with TypeScript
```typescript
// Simple state
const [query, setQuery] = useState<string>('');

// Object state
const [profile, setProfile] = useState<UserProfile | null>(null);

// Array state
const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
```

### Props with Children
```typescript
interface LayoutProps {
  children: React.ReactNode;
  className?: string;
}

export function Layout({ children, className }: LayoutProps) {
  return <div className={className}>{children}</div>;
}
```

### API Calls with Type Safety
```typescript
// Using the typed API service
import { tafsirAPI } from '@/services/tafsirApi';
import type { TafsirResponse } from '@/types';

const searchTafsir = async () => {
  try {
    const response: TafsirResponse = await tafsirAPI.search(
      query,
      'tafsir',
      userToken
    );
    setResults(response);
  } catch (error) {
    if (error instanceof RateLimitError) {
      showToast('Rate limit exceeded', 'warning');
    }
  }
};
```

### Custom Hooks with TypeScript
```typescript
// hooks/useSearch.ts
import { useState, useCallback } from 'react';
import type { TafsirResponse, SearchQuery } from '@/types';

interface UseSearchReturn {
  results: TafsirResponse | null;
  isLoading: boolean;
  error: string | null;
  search: (query: SearchQuery) => Promise<void>;
}

export function useSearch(): UseSearchReturn {
  const [results, setResults] = useState<TafsirResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (query: SearchQuery) => {
    // Implementation
  }, []);

  return { results, isLoading, error, search };
}
```

## 🎯 Priority Migration Order

1. **High Priority** (Migrate First):
   - `app/types/` - ✅ Already done
   - `app/services/tafsirApi.ts` - ✅ Already done
   - `app/context/AppContext.jsx` → `.tsx`
   - `app/components/auth/AuthWrapper.jsx` → `.tsx`

2. **Medium Priority**:
   - `app/components/search/SearchBar.jsx` → `.tsx`
   - `app/components/ui/Toast.jsx` → `.tsx`
   - `app/hooks/*.js` → `.ts`
   - `app/utils/*.js` → `.ts`

3. **Low Priority** (Can be gradual):
   - Other components
   - Page components
   - Test files

## 🚀 Running TypeScript

```bash
# Development (TypeScript checks automatically)
npm run dev

# Type checking only
npx tsc --noEmit

# Build (includes TypeScript compilation)
npm run build
```

## ⚠️ Common Issues and Solutions

### Issue: "Cannot find module '@/types'"
**Solution**: Make sure tsconfig.json paths are configured correctly (already done).

### Issue: "Property does not exist on type"
**Solution**: Add proper type definitions or use type assertions:
```typescript
// If you know the type
const data = response as TafsirResponse;

// For dynamic properties
const value = (obj as any).dynamicProperty;
```

### Issue: "Implicit any type"
**Solution**: Add explicit types:
```typescript
// Before
const handleClick = (e) => { }

// After
const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => { }
```

## 📚 VS Code Settings

Add to `.vscode/settings.json` for better TypeScript support:

```json
{
  "typescript.tsdk": "node_modules/typescript/lib",
  "typescript.enablePromptUseWorkspaceTsdk": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```

## ✨ Benefits You Now Have

1. **Type Safety**: Catch errors at compile time
2. **IntelliSense**: Better autocomplete in VS Code
3. **Refactoring**: Safer code changes with type checking
4. **Documentation**: Types serve as inline documentation
5. **Confidence**: Know your code is correct before runtime

## 🎉 Next Steps

1. Start migrating files one by one (use the priority list)
2. Run `npx tsc --noEmit` regularly to check for type errors
3. Use the typed API service for all backend calls
4. Gradually add stricter TypeScript rules as you migrate more files

The TypeScript setup is complete and ready for gradual migration!