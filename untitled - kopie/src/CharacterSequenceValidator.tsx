import React, { useEffect } from 'react';

type Props = {
  password: string;
  onValidation: (result: { valid: boolean; sequenceCount: number }) => void;
};

const CharacterSequenceValidator: React.FC<Props> = ({
  password,
  onValidation,
}) => {
  useEffect(() => {
    const getCharType = (c: string) => {
      if (/[a-z]/.test(c)) return 'lower';
      if (/[A-Z]/.test(c)) return 'upper';
      if (/\d/.test(c)) return 'number';
      if (/[!@#$%^&*]/.test(c)) return 'special';
      return null;
    };

    let count = 0;

    for (let i = 0; i <= password.length - 4; i++) {
      const slice = password.substring(i, i + 4);
      const types = slice.split('').map(getCharType);

      if (
        types.includes('lower') &&
        types.includes('upper') &&
        types.includes('number') &&
        types.includes('special')
      ) {
        count++;
      }
    }

    onValidation({ valid: count > 0, sequenceCount: count });
  }, [password, onValidation]);

  return null;
};

export default CharacterSequenceValidator;
