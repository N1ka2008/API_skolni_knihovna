import React, { useEffect } from 'react';

type Props = {
  password: string;
  createdAt: number | null;
  onValidation: (result: { valid: boolean; timeTaken: number }) => void;
};

const PasswordTimeValidator: React.FC<Props> = ({
  password,
  createdAt,
  onValidation,
}) => {
  useEffect(() => {
    if (!password || !createdAt) return;

    const now = Date.now();
    const timeTaken = (now - createdAt) / 1000;

    onValidation({
      valid: timeTaken >= 5,
      timeTaken: Number(timeTaken.toFixed(2)),
    });
  }, [password, createdAt]);

  return null;
};

export default PasswordTimeValidator;
