// ABOUTME: One conversation in the admin Chats table — who, title, size, last activity, crisis status.
// ABOUTME: Links to the read-only transcript.

import Link from "next/link";
import { Badge, TableCell } from "@/components/shared";
import { formatRelativeTime } from "@/lib/utils";
import type { AdminThread } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.chats;

interface ThreadRowProps {
  thread: AdminThread;
}

export function ThreadRow({ thread }: ThreadRowProps) {
  return (
    <tr className="transition-colors duration-150 hover:bg-mani-bg">
      <TableCell>
        <div className="font-medium">{thread.userNickname ?? STRINGS.anonymous}</div>
        <p className="mt-0.5 max-w-xs truncate text-sm text-mani-text-muted">
          {thread.userEmail ?? `${thread.userId.slice(0, 8)}...`}
        </p>
      </TableCell>
      <TableCell className="text-sm text-mani-text">{thread.title ?? STRINGS.untitledShort}</TableCell>
      <TableCell className="text-sm text-mani-text-muted">{thread.messageCount}</TableCell>
      <TableCell className="text-sm text-mani-text-muted">
        {formatRelativeTime(thread.lastMessageAt, {
          justNow: STRINGS.justNow,
          minutesAgoSuffix: STRINGS.minutesAgoSuffix,
          hoursAgoSuffix: STRINGS.hoursAgoSuffix,
          daysAgoSuffix: STRINGS.daysAgoSuffix,
        })}
      </TableCell>
      <TableCell>
        {thread.crisisDetected ? (
          <Badge variant="danger">{STRINGS.statusCrisis}</Badge>
        ) : (
          <Badge variant="success">{STRINGS.statusNormal}</Badge>
        )}
      </TableCell>
      <TableCell className="text-right">
        <Link
          href={`/admin/chats/${thread.id}`}
          className="text-sm font-medium text-mani-accent transition-colors duration-150 hover:text-mani-accent-hover"
        >
          {STRINGS.viewLink}
        </Link>
      </TableCell>
    </tr>
  );
}
