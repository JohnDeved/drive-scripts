import { h, render } from 'https://esm.sh/preact@10.19.2';
import { useState, useEffect, useCallback, useRef, useMemo } from 'https://esm.sh/preact@10.19.2/hooks';
import htm from 'https://esm.sh/htm@3.1.1';

// Initialize htm with Preact
const html = htm.bind(h);

export {
    html,
    render,
    useState,
    useEffect,
    useCallback,
    useRef,
    useMemo
};
