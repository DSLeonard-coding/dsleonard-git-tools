#!/bin/bash
git fetch --depth=15 origin "${THIS_COMMIT}"
CLEAN_TAG=$(echo "${THIS_TAG}" | sed -E 's/^v([0-9.]+)(([a-z]+)[0-9]*)?(.*)$/\3-v\1\4/')
CLEAN_TAG=$(echo $CLEAN_TAG | sed -E 's/^-?(.*)/\1/')
echo "CLEAN_TAG ${CLEAN_TAG} ${THIS_TAG}"

CURRENT_BRANCH="$CLEAN_TAG"
while [[ "$CURRENT_BRANCH" =~ ^.*v[0-9]+\.[0-9]+.*$ ]]; do
  CURRENT_BRANCH="${CURRENT_BRANCH%.*}"

  REMOTE_SHA=$(git ls-remote origin "refs/heads/$CURRENT_BRANCH" | cut -f1)

  if [[ -z "$REMOTE_SHA" ]]; then
    git push origin "${THIS_COMMIT}:refs/heads/$CURRENT_BRANCH"
    continue
  fi

  if git merge-base --is-ancestor "${REMOTE_SHA}" "${THIS_COMMIT}"; then
    git push origin "${THIS_COMMIT}:refs/heads/$CURRENT_BRANCH"
  else # try a full fetch
    git fetch --depth=10000 origin "${THIS_COMMIT}"
    if git merge-base --is-ancestor "${REMOTE_SHA}" "${THIS_COMMIT}"; then
      git push origin "${THIS_COMMIT}:refs/heads/$CURRENT_BRANCH"
    else
      echo "Skipping $CURRENT_BRANCH: not a fast-forward."
    fi
  fi
done
